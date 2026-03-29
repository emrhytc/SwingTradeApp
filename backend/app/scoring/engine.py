"""
Scoring engine. Converts raw indicator results into normalized component scores,
directional long/short scores, confidence, and the final verdict.

Each scorer function:
  - Takes the appropriate indicator result dataclass
  - Returns a (score_0_to_100, detail_string) tuple
  - Is pure: no side effects, no external calls
"""
import math
from dataclasses import dataclass
from typing import Tuple

from app.indicators.trend import TrendResult
from app.indicators.volatility import VolatilityResult
from app.indicators.chop import ChopResult
from app.indicators.participation import ParticipationResult
from app.schemas.analysis import (
    ComponentScore, ComponentScores, Decision, RiskLevel, StatusLevel
)
from app.scoring.weights import ScoringWeights, DecisionThresholds, DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS


# ─────────────────────────────────────────────
# Individual Component Scorers
# ─────────────────────────────────────────────

def score_trend(trend: TrendResult, direction: str = "long") -> Tuple[float, str]:
    """
    Score trend quality 0-100.
    direction: "long" or "short" — determines which directional sub-scores apply.
    """
    # 1. EMA Stack (0-40)
    stack = trend.ema_stack_score  # -4 to +4
    if direction == "long":
        # +4 = fully bullish = 40 pts
        ema_score = max(0.0, stack / 4.0) * 40
    else:
        # -4 = fully bearish = 40 pts for shorts
        ema_score = max(0.0, -stack / 4.0) * 40

    # 2. ADX Strength (0-30) — direction agnostic
    adx = trend.adx
    if adx >= 40:
        adx_score = 30
    elif adx >= 25:
        adx_score = 22
    elif adx >= 20:
        adx_score = 12
    else:
        adx_score = 0

    # 3. Price vs MAs (0-20)
    if direction == "long":
        above_count = trend.price_above_count
        price_score = {4: 20, 3: 15, 2: 8, 1: 3, 0: 0}[above_count]
    else:
        # For shorts, price *below* MAs is positive
        below_count = 4 - trend.price_above_count
        price_score = {4: 20, 3: 15, 2: 8, 1: 3, 0: 0}[below_count]

    # 4. Swing structure (0-10)
    if direction == "long":
        if trend.swing_structure == 1:
            swing_score = 10
        elif trend.swing_structure == 0:
            swing_score = 4
        else:
            swing_score = 0
    else:
        if trend.swing_structure == -1:
            swing_score = 10
        elif trend.swing_structure == 0:
            swing_score = 4
        else:
            swing_score = 0

    total = ema_score + adx_score + price_score + swing_score  # max=100

    # Build readable detail
    if direction == "long":
        dir_detail = f"EMA stack {'bullish' if stack > 0 else 'bearish'} (score={stack:+d}/4)"
    else:
        dir_detail = f"EMA stack {'bearish' if stack < 0 else 'bullish'} for shorts (score={stack:+d}/4)"

    detail = (
        f"{dir_detail}, ADX={adx:.1f}, "
        f"price above {trend.price_above_count}/4 EMAs, "
        f"structure: {trend.swing_detail}"
    )
    return min(100.0, total), detail


def score_volatility(vol: VolatilityResult) -> Tuple[float, str]:
    """Score volatility suitability 0-100. Goldilocks logic."""

    # 1. ATR Percentile (0-50) — sweet spot 30-70
    ap = vol.atr_percentile
    if 30 <= ap <= 70:
        atr_score = 50
    elif 20 <= ap < 30 or 70 < ap <= 80:
        atr_score = 35
    elif 10 <= ap < 20 or 80 < ap <= 90:
        atr_score = 15
    else:
        atr_score = 0  # extremes are bad

    # 2. BB Width Percentile (0-30) — same sweet spot logic
    bp = vol.bb_width_percentile
    if 30 <= bp <= 70:
        bb_score = 30
    elif 20 <= bp < 30 or 70 < bp <= 80:
        bb_score = 20
    elif 10 <= bp < 20 or 80 < bp <= 90:
        bb_score = 8
    else:
        bb_score = 0

    # 3. Volatility expansion bonus (0-20)
    if vol.is_expanding:
        expansion_score = 20  # waking up from compression = ideal
    elif vol.is_compressing:
        expansion_score = 5   # entering compression = caution
    elif vol.volatility_regime == "Extreme":
        expansion_score = 0
    else:
        expansion_score = 12  # stable is fine

    total = atr_score + bb_score + expansion_score

    detail = (
        f"ATR percentile={ap:.0f}%, BB width percentile={bp:.0f}%, "
        f"regime={vol.volatility_regime}"
    )
    return min(100.0, float(total)), detail


def score_chop(chop: ChopResult) -> Tuple[float, str]:
    """Score market cleanliness 0-100."""

    # 1. Efficiency Ratio (0-40)
    er = chop.efficiency_ratio
    if er >= 0.6:
        er_score = 40
    elif er >= 0.4:
        er_score = 25
    elif er >= 0.2:
        er_score = 10
    else:
        er_score = 0

    # 2. Chop Index (0-30)
    ci = chop.chop_index
    if ci < 38.2:
        ci_score = 30
    elif ci < 50:
        ci_score = 20
    elif ci < 61.8:
        ci_score = 8
    else:
        ci_score = 0

    # 3. Wick ratio (0-30)
    wr = chop.avg_wick_ratio
    if wr < 0.30:
        wick_score = 30
    elif wr < 0.50:
        wick_score = 20
    elif wr < 0.70:
        wick_score = 8
    else:
        wick_score = 0

    total = er_score + ci_score + wick_score

    detail = (
        f"Efficiency Ratio={er:.2f}, Chop Index={ci:.1f}, "
        f"Avg wick ratio={wr:.0%} — {chop.chop_label}"
    )
    return min(100.0, float(total)), detail


def score_participation(part: ParticipationResult, direction: str = "long") -> Tuple[float, str]:
    """Score participation quality 0-100."""

    # 1. Relative Volume (0-40)
    rv = part.relative_volume
    if rv >= 1.5:
        vol_score = 40
    elif rv >= 1.0:
        vol_score = 28
    elif rv >= 0.7:
        vol_score = 15
    else:
        vol_score = 0

    # 2. OBV Alignment (0-40)
    if part.obv_aligned:
        obv_score = 40
    else:
        obv_score = 0  # divergence is a red flag

    # 3. Breakout Volume Quality (0-20)
    bvq_score = part.breakout_volume_quality * 20

    total = vol_score + obv_score + bvq_score

    detail = (
        f"Relative volume={rv:.2f}x, OBV={'aligned' if part.obv_aligned else 'diverging'}, "
        f"Breakout vol quality={part.breakout_volume_quality:.0%}"
    )
    return min(100.0, float(total)), detail


def score_mtf(
    daily_stack: int,
    h4_stack: int,
    h1_stack: int,
    direction: str = "long",
) -> Tuple[float, str]:
    """
    Score multi-timeframe alignment 0-100.
    Stack values are ema_stack_score (-4 to +4) from each timeframe.
    """
    if direction == "long":
        # Positive stack = bullish alignment
        d_bull = daily_stack > 0
        h4_bull = h4_stack > 0
        h1_bull = h1_stack > 0
    else:
        d_bull = daily_stack < 0
        h4_bull = h4_stack < 0
        h1_bull = h1_stack < 0

    # 1D + 4H alignment (0-50)
    if d_bull and h4_bull:
        d_h4_score = 50
    elif d_bull or h4_bull:
        d_h4_score = 25
    else:
        d_h4_score = 0

    # 4H + 1H alignment (0-30)
    if h4_bull and h1_bull:
        h4_h1_score = 30
    elif h4_bull or h1_bull:
        h4_h1_score = 15
    else:
        h4_h1_score = 0

    # All three aligned (0-20 bonus)
    if d_bull and h4_bull and h1_bull:
        alignment_bonus = 20
    else:
        alignment_bonus = 0

    total = d_h4_score + h4_h1_score + alignment_bonus

    aligned_count = sum([d_bull, h4_bull, h1_bull])
    detail = (
        f"{'1D aligned' if d_bull else '1D opposing'}, "
        f"{'4H aligned' if h4_bull else '4H opposing'}, "
        f"{'1H aligned' if h1_bull else '1H opposing'} "
        f"— {aligned_count}/3 timeframes aligned for {direction}"
    )
    return min(100.0, float(total)), detail


def score_market_context() -> Tuple[float, str]:
    """
    Stub scorer. Returns neutral score.
    Replace with VIX, sector, benchmark analysis when available.
    """
    return 50.0, "Market context analysis not yet implemented (neutral score applied)"


# ─────────────────────────────────────────────
# Risk and Confidence
# ─────────────────────────────────────────────

def compute_risk_level(vol: VolatilityResult) -> RiskLevel:
    ap = vol.atr_percentile
    if ap > 85:
        return RiskLevel.EXTREME
    elif ap > 70:
        return RiskLevel.HIGH
    elif ap > 40:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


def compute_confidence(
    trend: TrendResult,
    chop: ChopResult,
    vol: VolatilityResult,
    mtf_score: float,
    has_full_mtf: bool,
) -> float:
    """
    Confidence = 100 minus penalties for conflicts, extremes, data issues.
    """
    confidence = 100.0

    # MTF conflict penalty
    if not has_full_mtf:
        confidence -= 15
    elif mtf_score < 30:
        confidence -= 20

    # Extreme volatility
    if vol.volatility_regime == "Extreme":
        confidence -= 15
    elif vol.atr_percentile < 10:
        confidence -= 10  # too compressed to read

    # ADX/Chop contradiction: strong ADX but high chop index
    if trend.adx > 25 and chop.chop_index > 61.8:
        confidence -= 15

    # Very low ADX = no clear signal
    if trend.adx < 15:
        confidence -= 10

    return max(10.0, min(100.0, confidence))


# ─────────────────────────────────────────────
# Final Score Assembly
# ─────────────────────────────────────────────

@dataclass
class ScoringResult:
    overall_score: float
    long_score: float
    short_score: float
    confidence: float
    risk_level: RiskLevel
    components_long: ComponentScores
    components_short: ComponentScores


def _to_status(score: float) -> StatusLevel:
    if score >= 75:
        return StatusLevel.STRONG
    elif score >= 55:
        return StatusLevel.MODERATE
    elif score >= 35:
        return StatusLevel.WEAK
    else:
        return StatusLevel.POOR


def _make_component(
    score: float,
    raw_contribution: float,
    label: str,
    detail: str,
) -> ComponentScore:
    return ComponentScore(
        score=round(score, 1),
        raw_score=round(raw_contribution, 1),
        label=label,
        status=_to_status(score),
        detail=detail,
    )


def run_scoring_engine(
    trend: TrendResult,
    vol: VolatilityResult,
    chop: ChopResult,
    part: ParticipationResult,
    # MTF stacks from higher timeframes (None if unavailable)
    daily_stack: int | None = None,
    h4_stack: int | None = None,
    h1_stack: int | None = None,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
    thresholds: DecisionThresholds = DEFAULT_THRESHOLDS,
) -> ScoringResult:

    weights.validate()

    # Use current timeframe stack as fallback for missing timeframes
    current_stack = trend.ema_stack_score
    daily_stack = daily_stack if daily_stack is not None else current_stack
    h4_stack = h4_stack if h4_stack is not None else current_stack
    h1_stack = h1_stack if h1_stack is not None else current_stack
    has_full_mtf = all(x is not None for x in [daily_stack, h4_stack, h1_stack])

    # Score each component for long direction
    trend_long, trend_long_detail = score_trend(trend, "long")
    trend_short, trend_short_detail = score_trend(trend, "short")
    vol_score, vol_detail = score_volatility(vol)
    chop_score, chop_detail = score_chop(chop)
    part_long, part_long_detail = score_participation(part, "long")
    part_short, part_short_detail = score_participation(part, "short")
    mtf_long, mtf_long_detail = score_mtf(daily_stack, h4_stack, h1_stack, "long")
    mtf_short, mtf_short_detail = score_mtf(daily_stack, h4_stack, h1_stack, "short")
    ctx_score, ctx_detail = score_market_context()

    # Weighted long score
    long_score = (
        trend_long * weights.trend +
        vol_score * weights.volatility +
        chop_score * weights.chop +
        part_long * weights.participation +
        mtf_long * weights.mtf +
        ctx_score * weights.context
    )

    # Weighted short score
    short_score = (
        trend_short * weights.trend +
        vol_score * weights.volatility +
        chop_score * weights.chop +
        part_short * weights.participation +
        mtf_short * weights.mtf +
        ctx_score * weights.context
    )

    overall_score = max(long_score, short_score)

    confidence = compute_confidence(trend, chop, vol, max(mtf_long, mtf_short), has_full_mtf)
    risk = compute_risk_level(vol)

    def make_long_components() -> ComponentScores:
        return ComponentScores(
            trend=_make_component(trend_long, trend_long * weights.trend, "Trend Quality", trend_long_detail),
            volatility=_make_component(vol_score, vol_score * weights.volatility, "Volatility Suitability", vol_detail),
            chop=_make_component(chop_score, chop_score * weights.chop, "Chop Cleanliness", chop_detail),
            participation=_make_component(part_long, part_long * weights.participation, "Participation Quality", part_long_detail),
            mtf_alignment=_make_component(mtf_long, mtf_long * weights.mtf, "MTF Alignment", mtf_long_detail),
            market_context=_make_component(ctx_score, ctx_score * weights.context, "Market Context", ctx_detail),
        )

    def make_short_components() -> ComponentScores:
        return ComponentScores(
            trend=_make_component(trend_short, trend_short * weights.trend, "Trend Quality", trend_short_detail),
            volatility=_make_component(vol_score, vol_score * weights.volatility, "Volatility Suitability", vol_detail),
            chop=_make_component(chop_score, chop_score * weights.chop, "Chop Cleanliness", chop_detail),
            participation=_make_component(part_short, part_short * weights.participation, "Participation Quality", part_short_detail),
            mtf_alignment=_make_component(mtf_short, mtf_short * weights.mtf, "MTF Alignment", mtf_short_detail),
            market_context=_make_component(ctx_score, ctx_score * weights.context, "Market Context", ctx_detail),
        )

    return ScoringResult(
        overall_score=round(overall_score, 1),
        long_score=round(long_score, 1),
        short_score=round(short_score, 1),
        confidence=round(confidence, 1),
        risk_level=risk,
        components_long=make_long_components(),
        components_short=make_short_components(),
    )


def score_to_decision(score: float, thresholds: DecisionThresholds = DEFAULT_THRESHOLDS) -> Decision:
    if score >= thresholds.suitable:
        return Decision.SUITABLE
    elif score >= thresholds.cautious:
        return Decision.CAUTIOUSLY_SUITABLE
    else:
        return Decision.NOT_SUITABLE
