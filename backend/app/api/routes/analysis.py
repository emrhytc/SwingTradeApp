"""
Analysis API routes.
Orchestrates the full pipeline: data → indicators → scoring → regime → explanation → response.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from app.config import settings
from app.schemas.analysis import (
    AnalysisResponse, AnalysisRequest, ScanRequest, ScanResponse,
    ScanResult, MTFAnalysisResponse, OHLCVBar,
    TechnicalState, IndicatorSnapshot, RegimeDirection,
)
from app.data.providers.base import DataRequest, MarketDataProvider
from app.data.providers.yfinance_provider import YFinanceProvider
from app.indicators.trend import compute_trend_indicators
from app.indicators.volatility import compute_volatility_indicators
from app.indicators.chop import compute_chop_indicators
from app.indicators.participation import compute_participation_indicators
from app.scoring.engine import run_scoring_engine, score_to_decision
from app.regime.classifier import classify_regime
from app.explanation.generator import generate_explanation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analysis"])

# Map common aliases (TradingView, broker notation) → yfinance ticker symbols
SYMBOL_ALIASES: dict[str, str] = {
    # Nasdaq 100 futures
    "NQ!1": "NQ=F", "NQ1!": "NQ=F", "NQ": "NQ=F",
    # S&P 500 futures
    "ES!1": "ES=F", "ES1!": "ES=F", "ES": "ES=F",
    # Dow Jones futures
    "YM!1": "YM=F", "YM1!": "YM=F", "YM": "YM=F",
    # Russell 2000 futures
    "RTY!1": "RTY=F", "RTY1!": "RTY=F",
    # Crude Oil futures
    "CL!1": "CL=F", "CL1!": "CL=F",
    # Gold futures / spot aliases
    "XAUUSD": "GC=F", "GC!1": "GC=F", "GC1!": "GC=F",
    # Silver futures / spot aliases
    "XAGUSD": "SI=F", "SI!1": "SI=F", "SI1!": "SI=F",
    # EUR/USD spot
    "EURUSD": "EURUSD=X",
    # GBP/USD spot
    "GBPUSD": "GBPUSD=X",
    # USD/JPY spot
    "USDJPY": "JPY=X",
    # VIX
    "VIX": "^VIX",
}


def _normalize_symbol(symbol: str) -> str:
    """Convert user-facing symbol aliases to yfinance-compatible tickers."""
    upper = symbol.upper().strip()
    return SYMBOL_ALIASES.get(upper, upper)

# Maps primary timeframe → (highest_ctx_tf, middle_ctx_tf)
CONTEXT_TIMEFRAMES: dict[str, tuple[str | None, str | None]] = {
    "15m": ("4H", "1H"),
    "1H":  ("1D", "4H"),
    "4H":  ("1D", None),
    "1D":  (None, None),
    "1W":  (None, None),
}

# Simple in-process TTL cache: {cache_key: (result, timestamp)}
_cache: dict = {}


def _get_provider() -> MarketDataProvider:
    return YFinanceProvider()


def _fetch_ema_stack(provider: MarketDataProvider, symbol: str, timeframe: str) -> int | None:
    """Fetch EMA stack score for a context timeframe. Returns None on failure."""
    try:
        df = provider.get_ohlcv(DataRequest(symbol=symbol, timeframe=timeframe, bars=500))
        return compute_trend_indicators(df).ema_stack_score
    except Exception as e:
        logger.warning("Could not fetch context stack for %s/%s: %s", symbol, timeframe, e)
        return None


def _cache_key(symbol: str, timeframe: str) -> str:
    return f"{symbol.upper()}:{timeframe}"


def _get_cached(key: str) -> Optional[AnalysisResponse]:
    if key in _cache:
        result, ts = _cache[key]
        if time.time() - ts < settings.CACHE_TTL_SECONDS:
            return result
        del _cache[key]
    return None


def _set_cached(key: str, result: AnalysisResponse) -> None:
    _cache[key] = (result, time.time())


def _df_to_chart_bars(df: pd.DataFrame) -> list[OHLCVBar]:
    """Convert OHLCV DataFrame to lightweight-charts compatible bar list."""
    bars = []
    for ts, row in df.tail(300).iterrows():
        ms = int(pd.Timestamp(ts).timestamp() * 1000)
        bars.append(OHLCVBar(
            timestamp=ms,
            open=round(float(row["open"]), 4),
            high=round(float(row["high"]), 4),
            low=round(float(row["low"]), 4),
            close=round(float(row["close"]), 4),
            volume=round(float(row["volume"]), 0),
        ))
    return bars


def _build_technical_state(
    trend, vol, chop, part,
    daily_stack=None, h4_stack=None, h1_stack=None,
    regime_direction=None,
    context_tfs: list[str] | None = None,
) -> TechnicalState:
    """Assemble the TechnicalState summary object."""

    # EMA alignment description
    s = trend.ema_stack_score
    if s >= 4:
        ema_desc = "20>50>100>200 (Fully Bullish)"
    elif s <= -4:
        ema_desc = "20<50<100<200 (Fully Bearish)"
    elif s > 0:
        ema_desc = f"Mostly bullish ({s:+d}/4 pairs aligned)"
    elif s < 0:
        ema_desc = f"Mostly bearish ({s:+d}/4 pairs aligned)"
    else:
        ema_desc = "Mixed / No clear alignment"

    # ADX status
    if trend.adx >= 35:
        adx_status = f"Very strong trend (ADX={trend.adx:.1f})"
    elif trend.adx >= 25:
        adx_status = f"Trending (ADX={trend.adx:.1f})"
    elif trend.adx >= 20:
        adx_status = f"Weak trend (ADX={trend.adx:.1f})"
    else:
        adx_status = f"No trend (ADX={trend.adx:.1f})"

    # Price vs EMAs
    count = trend.price_above_count
    price_desc = {
        4: "Above all EMAs (20/50/100/200)",
        3: f"Above 3/4 EMAs",
        2: f"Above 2/4 EMAs (mixed)",
        1: f"Below most EMAs",
        0: "Below all EMAs (20/50/100/200)",
    }[count]

    # Volatility regime
    vol_regime = (
        f"{vol.volatility_regime} (ATR pct={vol.atr_percentile:.0f}%, "
        f"BB width pct={vol.bb_width_percentile:.0f}%)"
    )

    # OBV
    obv_desc = (
        "Rising with price (Confirming)" if part.obv_aligned and trend.price_above_count >= 2
        else "Falling with price (Confirming)" if part.obv_aligned
        else "Diverging from price (Warning)"
    )

    # MTF
    _to_dir = lambda stack: (
        RegimeDirection.BULLISH if stack is not None and stack > 0
        else RegimeDirection.BEARISH if stack is not None and stack < 0
        else RegimeDirection.NEUTRAL
    )

    d_dir = _to_dir(daily_stack)
    h4_dir = _to_dir(h4_stack)
    h1_dir = _to_dir(h1_stack)

    mtf_conflict = len({d_dir, h4_dir, h1_dir}) > 1
    mtf_aligned_count = sum(1 for d in [d_dir, h4_dir, h1_dir] if d == regime_direction)
    mtf_summary = (
        f"{mtf_aligned_count}/3 timeframes aligned"
        + (" — conflict detected" if mtf_conflict else "")
    )

    # Chop status
    chop_desc = f"{chop.chop_label} (CI={chop.chop_index:.1f}, ER={chop.efficiency_ratio:.2f})"

    # Participation status
    part_desc = (
        f"{part.participation_label} "
        f"(RelVol={part.relative_volume:.2f}x, "
        f"OBV={'aligned' if part.obv_aligned else 'diverging'})"
    )

    return TechnicalState(
        ema_alignment=ema_desc,
        adx_value=round(trend.adx, 1),
        adx_status=adx_status,
        price_vs_emas=price_desc,
        swing_structure=trend.swing_detail,
        trend_direction=regime_direction or RegimeDirection.NEUTRAL,
        atr_value=round(vol.atr, 4),
        atr_percentile=round(vol.atr_percentile, 1),
        bb_width_percentile=round(vol.bb_width_percentile, 1),
        volatility_regime=vol_regime,
        efficiency_ratio=round(chop.efficiency_ratio, 3),
        chop_index=round(chop.chop_index, 1),
        avg_wick_ratio=round(chop.avg_wick_ratio, 3),
        chop_status=chop_desc,
        relative_volume=round(part.relative_volume, 2),
        obv_trend=obv_desc,
        participation_status=part_desc,
        daily_trend=d_dir,
        h4_trend=h4_dir,
        h1_trend=h1_dir,
        mtf_conflict=mtf_conflict,
        mtf_summary=mtf_summary,
        context_tfs=context_tfs or ["1D", "4H", "1H"],
    )


def _run_analysis_pipeline(
    symbol: str,
    timeframe: str,
    include_chart_data: bool = True,
    daily_stack: int | None = None,
    h4_stack: int | None = None,
    h1_stack: int | None = None,
) -> AnalysisResponse:
    """Core pipeline: fetch → indicators → score → explain → build response."""

    provider = _get_provider()
    req = DataRequest(symbol=symbol, timeframe=timeframe, bars=500)

    try:
        df = provider.get_ohlcv(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Data fetch error for %s/%s: %s", symbol, timeframe, e)
        raise HTTPException(status_code=502, detail=f"Data provider error: {e}")

    # Run indicators
    trend = compute_trend_indicators(df)

    # Auto-fetch context TF stacks when not explicitly provided
    ctx_high, ctx_mid = CONTEXT_TIMEFRAMES.get(timeframe, (None, None))
    if daily_stack is None and ctx_high:
        daily_stack = _fetch_ema_stack(provider, symbol, ctx_high)
    if h4_stack is None and ctx_mid:
        h4_stack = _fetch_ema_stack(provider, symbol, ctx_mid)
    # h1_stack = primary TF's own EMA trend (for the "primary" badge in the UI)
    if h1_stack is None:
        h1_stack = trend.ema_stack_score

    # Display labels for the 3 MTF trend badges
    context_tfs = [
        ctx_high or "1D",
        ctx_mid or "4H",
        timeframe,
    ]
    vol = compute_volatility_indicators(df)
    chop = compute_chop_indicators(df)
    part = compute_participation_indicators(df)

    # Score
    scoring = run_scoring_engine(
        trend, vol, chop, part,
        daily_stack=daily_stack,
        h4_stack=h4_stack,
        h1_stack=h1_stack,
    )

    # Regime
    regime, regime_direction = classify_regime(trend, vol, chop)

    # Decision
    decision = score_to_decision(scoring.overall_score)

    # Explanation
    explanation = generate_explanation(
        trend, vol, chop, part,
        regime, regime_direction, decision,
        scoring.long_score, scoring.short_score,
    )

    # Technical state
    tech_state = _build_technical_state(
        trend, vol, chop, part,
        daily_stack=daily_stack,
        h4_stack=h4_stack,
        h1_stack=h1_stack,
        regime_direction=regime_direction,
        context_tfs=context_tfs,
    )

    # Raw indicator snapshot
    indicators = IndicatorSnapshot(
        ema20=round(trend.ema20, 4),
        ema50=round(trend.ema50, 4),
        ema100=round(trend.ema100, 4),
        ema200=round(trend.ema200, 4),
        adx=round(trend.adx, 2),
        plus_di=round(trend.plus_di, 2),
        minus_di=round(trend.minus_di, 2),
        atr=round(vol.atr, 4),
        bb_upper=round(vol.bb_upper, 4),
        bb_middle=round(vol.bb_middle, 4),
        bb_lower=round(vol.bb_lower, 4),
        obv=None,  # OBV is a running total; not useful as a single number
        relative_volume=round(part.relative_volume, 2),
    )

    chart_data = _df_to_chart_bars(df) if include_chart_data else None

    # Use long components as primary display (highest relevance)
    components = scoring.components_long if scoring.long_score >= scoring.short_score else scoring.components_short

    return AnalysisResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        analyzed_at=datetime.now(timezone.utc),
        overall_decision=decision,
        overall_score=scoring.overall_score,
        long_score=scoring.long_score,
        short_score=scoring.short_score,
        confidence=scoring.confidence,
        risk_level=scoring.risk_level,
        regime=regime,
        regime_direction=regime_direction,
        components=components,
        positive_factors=explanation.positive_factors,
        negative_factors=explanation.negative_factors,
        conflicting_factors=explanation.conflicting_factors,
        summary=explanation.summary,
        technical_state=tech_state,
        indicators=indicators,
        chart_data=chart_data,
    )


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.get("/analysis", response_model=AnalysisResponse)
async def get_analysis(
    symbol: str = Query(..., description="Ticker symbol e.g. AAPL, BTC-USD"),
    timeframe: str = Query("1D", description="Timeframe: 15m, 1H, 4H, 1D, 1W"),
    include_chart_data: bool = Query(True, description="Include OHLCV bars in response"),
    use_cache: bool = Query(True),
):
    """
    Full swing trade suitability analysis for a single symbol and timeframe.
    """
    symbol = _normalize_symbol(symbol)
    key = _cache_key(symbol, timeframe)

    if use_cache:
        cached = _get_cached(key)
        if cached:
            logger.info("Cache hit: %s", key)
            return cached

    result = _run_analysis_pipeline(symbol, timeframe, include_chart_data)
    _set_cached(key, result)
    return result


@router.get("/analysis/mtf", response_model=MTFAnalysisResponse)
async def get_mtf_analysis(
    symbol: str = Query(..., description="Ticker symbol"),
):
    """
    Full multi-timeframe analysis: 1D, 4H, 1H computed together for alignment scoring.
    """
    symbol = _normalize_symbol(symbol)

    # Fetch daily first to get the stack for MTF context
    daily_result = None
    h4_result = None
    h1_result = None
    errors = {}

    try:
        daily_result = _run_analysis_pipeline(symbol, "1D", include_chart_data=False)
    except Exception as e:
        errors["1D"] = str(e)

    d_stack = daily_result.technical_state.daily_trend if daily_result else None
    daily_stack_int = None
    if daily_result:
        trend_ind = compute_trend_indicators(
            _get_provider().get_ohlcv(DataRequest(symbol, "1D", 500))
        )
        daily_stack_int = trend_ind.ema_stack_score

    try:
        h4_result = _run_analysis_pipeline(
            symbol, "4H", include_chart_data=False,
            daily_stack=daily_stack_int,
        )
    except Exception as e:
        errors["4H"] = str(e)

    h4_stack_int = None
    if h4_result:
        try:
            trend_h4 = compute_trend_indicators(
                _get_provider().get_ohlcv(DataRequest(symbol, "4H", 500))
            )
            h4_stack_int = trend_h4.ema_stack_score
        except Exception:
            pass

    try:
        h1_result = _run_analysis_pipeline(
            symbol, "1H", include_chart_data=False,
            daily_stack=daily_stack_int,
            h4_stack=h4_stack_int,
        )
    except Exception as e:
        errors["1H"] = str(e)

    # Overall alignment score
    available = [r for r in [daily_result, h4_result, h1_result] if r is not None]
    if len(available) == 0:
        raise HTTPException(status_code=502, detail=f"All timeframes failed: {errors}")

    scores = [r.overall_score for r in available]
    alignment_score = sum(scores) / len(scores)

    directions = [r.regime_direction for r in available]
    same_direction = len(set(directions)) == 1
    alignment_summary = (
        f"All {len(available)} timeframes aligned in {directions[0].value} direction."
        if same_direction
        else f"Timeframes conflict: {', '.join(d.value for d in directions)}. Reduce position size."
    )

    return MTFAnalysisResponse(
        symbol=symbol,
        analyzed_at=datetime.now(timezone.utc),
        daily=daily_result,
        h4=h4_result,
        h1=h1_result,
        alignment_score=round(alignment_score, 1),
        alignment_summary=alignment_summary,
    )


@router.post("/scanner", response_model=ScanResponse)
async def scan_symbols(request: ScanRequest):
    """
    Scan multiple symbols and return suitability rankings.
    """
    results = []
    for symbol in request.symbols:
        try:
            analysis = _run_analysis_pipeline(
                _normalize_symbol(symbol), request.timeframe, include_chart_data=False
            )
            results.append(ScanResult(
                symbol=symbol.upper(),
                overall_decision=analysis.overall_decision,
                overall_score=analysis.overall_score,
                long_score=analysis.long_score,
                short_score=analysis.short_score,
                regime=analysis.regime,
                regime_direction=analysis.regime_direction,
                summary=analysis.summary,
            ))
        except HTTPException as e:
            results.append(ScanResult(
                symbol=symbol.upper(),
                overall_decision=None,
                overall_score=0,
                long_score=0,
                short_score=0,
                regime=None,
                regime_direction=None,
                summary="",
                error=e.detail,
            ))
        except Exception as e:
            results.append(ScanResult(
                symbol=symbol.upper(),
                overall_decision=None,
                overall_score=0,
                long_score=0,
                short_score=0,
                regime=None,
                regime_direction=None,
                summary="",
                error=str(e),
            ))

    # Sort by overall score descending
    results.sort(key=lambda r: r.overall_score, reverse=True)

    return ScanResponse(
        results=results,
        scanned_at=datetime.now(timezone.utc),
        timeframe=request.timeframe,
    )
