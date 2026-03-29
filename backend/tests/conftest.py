"""
Shared test fixtures and synthetic market data generators.
Tests must never make real network calls — all data is generated here.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def _make_ohlcv(
    n: int = 300,
    start_price: float = 100.0,
    trend: float = 0.003,       # daily drift
    volatility: float = 0.015,  # daily std
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data with a configurable trend and volatility.
    Returns a properly indexed DataFrame ready for indicator computation.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=datetime.utcnow(), periods=n, freq="D")

    returns = rng.normal(trend, volatility, n)
    close = start_price * np.cumprod(1 + returns)

    noise_h = rng.uniform(0.002, 0.015, n)
    noise_l = rng.uniform(0.002, 0.015, n)
    high = close * (1 + noise_h)
    low = close * (1 - noise_l)
    open_ = low + rng.uniform(0, 1, n) * (high - low)
    volume = rng.uniform(800_000, 3_000_000, n)

    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)
    df.index.name = "datetime"
    return df


@pytest.fixture
def trending_up_df():
    """Strong uptrend: high drift, moderate volatility."""
    return _make_ohlcv(n=300, trend=0.006, volatility=0.012, seed=1)


@pytest.fixture
def trending_down_df():
    """Strong downtrend."""
    return _make_ohlcv(n=300, trend=-0.006, volatility=0.012, seed=2)


@pytest.fixture
def choppy_df():
    """Choppy market: near-zero drift, high volatility."""
    return _make_ohlcv(n=300, trend=0.0, volatility=0.025, seed=3)


@pytest.fixture
def low_vol_df():
    """Low volatility range-bound market."""
    return _make_ohlcv(n=300, trend=0.0001, volatility=0.004, seed=4)


@pytest.fixture
def high_vol_df():
    """High volatility trending market."""
    return _make_ohlcv(n=300, trend=0.004, volatility=0.035, seed=5)
