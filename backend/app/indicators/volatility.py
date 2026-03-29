"""
Volatility suitability indicators.
ATR, Bollinger Band width, and volatility regime detection.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from app.config import settings


@dataclass
class VolatilityResult:
    atr: float
    atr_percentile: float          # 0-100 percentile vs lookback window
    bb_width: float                # (upper - lower) / middle
    bb_width_percentile: float     # 0-100 percentile vs lookback window
    bb_upper: float
    bb_middle: float
    bb_lower: float
    is_expanding: bool             # ATR expanding from recent low
    is_compressing: bool           # ATR compressing from recent high
    volatility_regime: str         # "Expanding", "Compressing", "Stable", "Extreme"


def compute_atr(df: pd.DataFrame, period: int = None) -> pd.Series:
    """True Range and ATR via Wilder smoothing."""
    period = period or settings.ATR_PERIOD
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    return atr


def compute_bollinger_bands(
    df: pd.DataFrame, period: int = None, std: float = None
) -> pd.DataFrame:
    """Compute Bollinger Bands. Returns df with bb_upper, bb_middle, bb_lower, bb_width columns."""
    period = period or settings.BB_PERIOD
    std = std or settings.BB_STD
    out = df.copy()

    out["bb_middle"] = out["close"].rolling(period).mean()
    rolling_std = out["close"].rolling(period).std()
    out["bb_upper"] = out["bb_middle"] + std * rolling_std
    out["bb_lower"] = out["bb_middle"] - std * rolling_std
    out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_middle"].replace(0, np.nan)

    return out


def _percentile_of_latest(series: pd.Series, lookback: int) -> float:
    """
    Compute what percentile the latest value is relative to the
    last `lookback` values (including itself).
    Returns 0-100.
    """
    window = series.dropna().tail(lookback)
    if len(window) < 10:
        return 50.0
    latest = window.iloc[-1]
    return float((window < latest).mean() * 100)


def _detect_volatility_regime(atr: pd.Series, lookback: int = 20) -> tuple[bool, bool, str]:
    """
    Detect whether ATR is expanding or contracting vs recent average.
    Returns: (is_expanding, is_compressing, regime_label)
    """
    recent = atr.dropna().tail(lookback)
    if len(recent) < 5:
        return False, False, "Unknown"

    current = recent.iloc[-1]
    prior_avg = recent.iloc[:-5].mean() if len(recent) > 5 else recent.mean()
    recent_low = recent.tail(10).min()
    recent_high = recent.tail(10).max()

    atr_pct = _percentile_of_latest(atr, 252)

    if atr_pct > 85:
        return False, False, "Extreme"

    # Expanding: current ATR above its 20-bar average and rising from a recent low
    is_expanding = current > prior_avg * 1.1 and current > recent_low * 1.15
    # Compressing: current ATR below average and falling
    is_compressing = current < prior_avg * 0.9 and current < recent_high * 0.85

    if is_expanding:
        return True, False, "Expanding"
    elif is_compressing:
        return False, True, "Compressing"
    else:
        return False, False, "Stable"


def compute_volatility_indicators(df: pd.DataFrame) -> VolatilityResult:
    """Run full volatility analysis. Returns VolatilityResult."""
    lookback = settings.ATR_PERCENTILE_LOOKBACK

    atr_series = compute_atr(df)
    df_bb = compute_bollinger_bands(df)

    atr_latest = float(atr_series.iloc[-1])
    atr_pct = _percentile_of_latest(atr_series, lookback)

    bb_width_series = df_bb["bb_width"]
    bb_width_latest = float(bb_width_series.iloc[-1])
    bb_width_pct = _percentile_of_latest(bb_width_series, lookback)

    is_expanding, is_compressing, regime = _detect_volatility_regime(atr_series)

    last = df_bb.iloc[-1]

    return VolatilityResult(
        atr=atr_latest,
        atr_percentile=atr_pct,
        bb_width=bb_width_latest,
        bb_width_percentile=bb_width_pct,
        bb_upper=float(last["bb_upper"]),
        bb_middle=float(last["bb_middle"]),
        bb_lower=float(last["bb_lower"]),
        is_expanding=is_expanding,
        is_compressing=is_compressing,
        volatility_regime=regime,
    )
