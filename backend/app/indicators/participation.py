"""
Participation and conviction indicators.
OBV, relative volume, and volume-on-breakout quality.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from app.config import settings


@dataclass
class ParticipationResult:
    relative_volume: float     # current vol / avg vol
    obv_slope: float           # OBV slope over recent N bars (normalized)
    obv_aligned: bool          # OBV trending in same direction as price
    breakout_volume_quality: float  # 0-1: quality of volume on recent large moves
    participation_label: str   # "Strong", "Moderate", "Weak", "Absent"


def compute_obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume. Adds cumulative volume signed by close direction."""
    direction = np.sign(df["close"].diff()).fillna(0)
    obv = (direction * df["volume"]).cumsum()
    return obv


def compute_relative_volume(df: pd.DataFrame, period: int = None) -> float:
    """
    Latest bar volume relative to rolling average.
    >1.5 = strong participation, <0.7 = low participation.
    """
    period = period or settings.VOLUME_AVG_PERIOD
    avg_vol = df["volume"].rolling(period).mean().iloc[-1]
    if avg_vol == 0 or np.isnan(avg_vol):
        return 1.0
    return float(df["volume"].iloc[-1] / avg_vol)


def _obv_slope_and_alignment(
    df: pd.DataFrame, obv: pd.Series, period: int = None
) -> tuple[float, bool]:
    """
    Compute normalized OBV slope and check if it aligns with price direction.
    Returns (normalized_slope, is_aligned_with_price)
    """
    period = period or settings.OBV_SLOPE_PERIOD
    if len(obv) < period + 1:
        return 0.0, True

    obv_recent = obv.tail(period + 1)
    price_recent = df["close"].tail(period + 1)

    # Normalize slope by mean OBV to make it comparable across assets
    obv_mean = obv_recent.abs().mean()
    if obv_mean == 0:
        return 0.0, True

    obv_change = obv_recent.iloc[-1] - obv_recent.iloc[0]
    price_change = price_recent.iloc[-1] - price_recent.iloc[0]

    normalized_slope = obv_change / obv_mean
    is_aligned = (obv_change > 0) == (price_change > 0)

    return float(normalized_slope), is_aligned


def _breakout_volume_quality(df: pd.DataFrame, lookback: int = 20) -> float:
    """
    Score volume quality on breakout bars (large range bars).
    A good breakout environment has high volume on large range bars.
    Returns 0-1.
    """
    recent = df.tail(lookback).copy()
    avg_vol = recent["volume"].mean()
    if avg_vol == 0:
        return 0.5

    bar_range = recent["high"] - recent["low"]
    avg_range = bar_range.mean()

    # Identify "breakout" bars: range > 1.2x average range
    large_bars = bar_range > avg_range * 1.2
    if large_bars.sum() == 0:
        return 0.5

    vol_on_large = recent.loc[large_bars, "volume"].mean()
    score = min(1.0, vol_on_large / (avg_vol * 1.5))
    return float(score)


def compute_participation_indicators(df: pd.DataFrame) -> ParticipationResult:
    """Run full participation analysis. Returns ParticipationResult."""
    rel_vol = compute_relative_volume(df)
    obv = compute_obv(df)
    obv_slope, obv_aligned = _obv_slope_and_alignment(df, obv)
    bvq = _breakout_volume_quality(df)

    # Classify participation
    if rel_vol >= 1.5 and obv_aligned:
        label = "Strong"
    elif rel_vol >= 1.0 and obv_aligned:
        label = "Moderate"
    elif not obv_aligned:
        label = "Diverging (OBV conflict)"
    elif rel_vol < 0.7:
        label = "Absent"
    else:
        label = "Weak"

    return ParticipationResult(
        relative_volume=rel_vol,
        obv_slope=obv_slope,
        obv_aligned=obv_aligned,
        breakout_volume_quality=bvq,
        participation_label=label,
    )
