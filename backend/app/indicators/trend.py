"""
Trend quality indicators.
All functions accept a pandas DataFrame with OHLCV columns and return
the same DataFrame with additional computed columns.
Functions are pure: they do not modify the input in place.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from app.config import settings


@dataclass
class TrendResult:
    # EMA values (latest bar)
    ema20: float
    ema50: float
    ema100: float
    ema200: float

    # EMA slopes (percent change over last 5 bars)
    ema20_slope: float
    ema50_slope: float

    # Stack alignment score: count of how many EMAs are in bullish order
    # 4 = 20>50>100>200 (fully bullish)
    # -4 = 20<50<100<200 (fully bearish)
    ema_stack_score: int  # -4 to +4

    # Price vs each EMA
    price_above_ema20: bool
    price_above_ema50: bool
    price_above_ema100: bool
    price_above_ema200: bool
    price_above_count: int  # 0-4

    # ADX
    adx: float
    plus_di: float
    minus_di: float

    # Swing structure
    # +1 = HH+HL (bullish structure), -1 = LH+LL (bearish), 0 = mixed
    swing_structure: int
    swing_detail: str


def compute_emas(df: pd.DataFrame) -> pd.DataFrame:
    """Compute EMA 20/50/100/200. Returns new DataFrame with EMA columns added."""
    out = df.copy()
    for period in settings.EMA_PERIODS:
        out[f"ema{period}"] = out["close"].ewm(span=period, adjust=False).mean()
    return out


def compute_adx(df: pd.DataFrame, period: int = None) -> pd.DataFrame:
    """
    Compute ADX, +DI, -DI using Wilder's smoothing.
    Adds columns: adx, plus_di, minus_di
    """
    period = period or settings.ADX_PERIOD
    out = df.copy()

    high = out["high"]
    low = out["low"]
    close = out["close"]

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    # Wilder smoothing (equivalent to EMA with alpha=1/period)
    atr_wilder = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di_smooth = plus_dm.ewm(alpha=1 / period, adjust=False).mean()
    minus_di_smooth = minus_dm.ewm(alpha=1 / period, adjust=False).mean()

    out["plus_di"] = 100 * plus_di_smooth / atr_wilder
    out["minus_di"] = 100 * minus_di_smooth / atr_wilder

    dx = 100 * (out["plus_di"] - out["minus_di"]).abs() / (out["plus_di"] + out["minus_di"]).replace(0, np.nan)
    out["adx"] = dx.ewm(alpha=1 / period, adjust=False).mean()

    return out


def detect_swing_structure(df: pd.DataFrame, lookback: int = None) -> Tuple[int, str]:
    """
    Detect Higher Highs / Higher Lows or Lower Highs / Lower Lows
    over the recent lookback window.

    Returns:
        (structure_score, description)
        structure_score: +1 = HH+HL, -1 = LH+LL, 0 = mixed
    """
    lookback = lookback or settings.SWING_LOOKBACK
    window = df.tail(lookback)

    if len(window) < 6:
        return 0, "Insufficient data"

    highs = window["high"].values
    lows = window["low"].values

    # Find local swing highs/lows using simple pivot detection
    swing_highs = _find_pivots(highs, pivot_type="high")
    swing_lows = _find_pivots(lows, pivot_type="low")

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return 0, "Not enough swing points"

    # Check last two swing highs
    hh = swing_highs[-1] > swing_highs[-2]
    lh = swing_highs[-1] < swing_highs[-2]

    # Check last two swing lows
    hl = swing_lows[-1] > swing_lows[-2]
    ll = swing_lows[-1] < swing_lows[-2]

    if hh and hl:
        return 1, "Higher Highs / Higher Lows (Bullish structure)"
    elif lh and ll:
        return -1, "Lower Highs / Lower Lows (Bearish structure)"
    elif hh and ll:
        return 0, "Higher Highs / Lower Lows (Broadening — mixed)"
    elif lh and hl:
        return 0, "Lower Highs / Higher Lows (Compression — neutral)"
    else:
        return 0, "Mixed swing structure"


def _find_pivots(values: np.ndarray, pivot_type: str, n: int = 2) -> List[float]:
    """
    Find pivot highs or lows in a 1D array.
    A pivot high at index i: values[i] > values[i-n] and values[i] > values[i+1..i+n]
    Returns list of pivot values.
    """
    pivots = []
    for i in range(n, len(values) - n):
        if pivot_type == "high":
            if all(values[i] > values[i - j] for j in range(1, n + 1)) and \
               all(values[i] > values[i + j] for j in range(1, n + 1)):
                pivots.append(values[i])
        else:
            if all(values[i] < values[i - j] for j in range(1, n + 1)) and \
               all(values[i] < values[i + j] for j in range(1, n + 1)):
                pivots.append(values[i])
    return pivots


def compute_trend_indicators(df: pd.DataFrame) -> TrendResult:
    """
    Run full trend analysis on a DataFrame. Returns a TrendResult.
    Requires at least 200 bars for reliable EMA200.
    """
    df = compute_emas(df)
    df = compute_adx(df)

    last = df.iloc[-1]
    close = last["close"]

    ema20 = last["ema20"]
    ema50 = last["ema50"]
    ema100 = last["ema100"]
    ema200 = last["ema200"]

    # Slope: percent change of EMA over last 5 bars
    n = min(5, len(df) - 1)
    ema20_slope = (df["ema20"].iloc[-1] - df["ema20"].iloc[-n - 1]) / df["ema20"].iloc[-n - 1] * 100
    ema50_slope = (df["ema50"].iloc[-1] - df["ema50"].iloc[-n - 1]) / df["ema50"].iloc[-n - 1] * 100

    # EMA stack: compare each consecutive pair
    # +1 if in bullish order, -1 if in bearish order
    pairs = [(ema20, ema50), (ema50, ema100), (ema100, ema200)]
    stack_score = sum(1 if a > b else -1 for a, b in pairs)
    # Normalize to -4..+4 range: actually we have 3 pairs so range is -3 to +3
    # Add the 4th check: 20 vs 200
    if ema20 > ema200:
        stack_score += 1
    else:
        stack_score -= 1
    # stack_score is now -4 to +4

    price_above = {
        20: close > ema20,
        50: close > ema50,
        100: close > ema100,
        200: close > ema200,
    }
    price_above_count = sum(price_above.values())

    adx = float(last.get("adx", 0) or 0)
    plus_di = float(last.get("plus_di", 0) or 0)
    minus_di = float(last.get("minus_di", 0) or 0)

    swing_score, swing_detail = detect_swing_structure(df)

    return TrendResult(
        ema20=float(ema20),
        ema50=float(ema50),
        ema100=float(ema100),
        ema200=float(ema200),
        ema20_slope=float(ema20_slope),
        ema50_slope=float(ema50_slope),
        ema_stack_score=stack_score,
        price_above_ema20=price_above[20],
        price_above_ema50=price_above[50],
        price_above_ema100=price_above[100],
        price_above_ema200=price_above[200],
        price_above_count=price_above_count,
        adx=adx,
        plus_di=plus_di,
        minus_di=minus_di,
        swing_structure=swing_score,
        swing_detail=swing_detail,
    )
