"""
Market chop and cleanliness indicators.
Efficiency Ratio, Chop Index, wick ratio, and MA cross frequency.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from app.config import settings


@dataclass
class ChopResult:
    efficiency_ratio: float   # 0-1: 1 = perfectly directional, 0 = pure noise
    chop_index: float         # 0-100: <38.2 = trending, >61.8 = choppy
    avg_wick_ratio: float     # 0-1: wick size / total range (lower = cleaner)
    ma_cross_frequency: float # crosses per bar over recent N bars (lower = cleaner)
    chop_label: str           # "Clean Trend", "Moderate", "Choppy", "Very Choppy"


def compute_efficiency_ratio(close: pd.Series, period: int = None) -> pd.Series:
    """
    Kaufman's Efficiency Ratio.
    ER = abs(net change over N bars) / sum(abs(1-bar changes) for N bars)
    Range: 0 (chaotic) to 1 (perfectly directional).
    """
    period = period or settings.EFFICIENCY_RATIO_PERIOD
    direction = close.diff(period).abs()
    volatility = close.diff(1).abs().rolling(period).sum()
    er = direction / volatility.replace(0, np.nan)
    return er.clip(0, 1)


def compute_chop_index(df: pd.DataFrame, period: int = None) -> pd.Series:
    """
    Chop Index = 100 * log10(sum(ATR1, N) / (highest_high - lowest_low)) / log10(N)
    Range: 0-100
    <38.2 = strong trend, >61.8 = high chop
    """
    period = period or settings.CHOP_PERIOD

    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)

    atr1_sum = tr.rolling(period).sum()
    highest_high = df["high"].rolling(period).max()
    lowest_low = df["low"].rolling(period).min()

    hl_range = (highest_high - lowest_low).replace(0, np.nan)
    ci = 100 * np.log10(atr1_sum / hl_range) / np.log10(period)
    return ci.clip(0, 100)


def compute_avg_wick_ratio(df: pd.DataFrame, lookback: int = 20) -> float:
    """
    Average ratio of wick size to total bar range over last N bars.
    Low ratio = clean bodies, high ratio = wick-heavy / indecisive bars.
    Returns 0-1.
    """
    recent = df.tail(lookback).copy()
    total_range = recent["high"] - recent["low"]
    body = (recent["close"] - recent["open"]).abs()
    wick = total_range - body

    # Avoid division by zero on doji bars
    ratio = (wick / total_range.replace(0, np.nan)).fillna(0.5)
    return float(ratio.mean())


def compute_ma_cross_frequency(
    df: pd.DataFrame, ema_period: int = 50, lookback: int = 20
) -> float:
    """
    Count how often the close price crosses the EMA(period) in the last N bars.
    Normalize by lookback to get crosses-per-bar.
    High frequency = choppy market rotating around the mean.
    """
    ema = df["close"].ewm(span=ema_period, adjust=False).mean()
    above = df["close"] > ema
    crosses = (above != above.shift(1)).tail(lookback).sum()
    return float(crosses) / lookback


def compute_chop_indicators(df: pd.DataFrame) -> ChopResult:
    """Run full chop analysis. Returns ChopResult."""
    er_series = compute_efficiency_ratio(df["close"])
    ci_series = compute_chop_index(df)

    er = float(er_series.dropna().iloc[-1]) if not er_series.dropna().empty else 0.3
    ci = float(ci_series.dropna().iloc[-1]) if not ci_series.dropna().empty else 50.0
    wick_ratio = compute_avg_wick_ratio(df)
    ma_cross_freq = compute_ma_cross_frequency(df)

    # Classify
    if er > 0.5 and ci < 45:
        label = "Clean Trend"
    elif er > 0.35 and ci < 55:
        label = "Moderate"
    elif ci > 61.8 or er < 0.2:
        label = "Very Choppy"
    else:
        label = "Choppy"

    return ChopResult(
        efficiency_ratio=er,
        chop_index=ci,
        avg_wick_ratio=wick_ratio,
        ma_cross_frequency=ma_cross_freq,
        chop_label=label,
    )
