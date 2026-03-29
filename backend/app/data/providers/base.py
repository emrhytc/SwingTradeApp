"""
Abstract base class for market data providers.
All data sources must implement this interface so the analysis pipeline
never depends on a specific provider.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import pandas as pd


SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1H", "4H", "1D", "1W"]


@dataclass
class DataRequest:
    symbol: str
    timeframe: str  # e.g. "1D", "4H", "1H"
    bars: int = 500  # number of bars to fetch


class MarketDataProvider(ABC):
    """
    Interface all data providers must implement.
    Returns a pandas DataFrame with columns: open, high, low, close, volume
    indexed by datetime (UTC).
    """

    @abstractmethod
    def get_ohlcv(self, request: DataRequest) -> pd.DataFrame:
        """
        Fetch OHLCV bars. Returns DataFrame with DatetimeIndex and columns:
        open, high, low, close, volume (all float).
        Raises ValueError on invalid symbol/timeframe.
        Raises RuntimeError on provider failure.
        """
        ...

    @abstractmethod
    def supports_timeframe(self, timeframe: str) -> bool:
        """Returns True if this provider can deliver the requested timeframe."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier string."""
        ...

    def validate_dataframe(self, df: pd.DataFrame, request: DataRequest) -> pd.DataFrame:
        """Shared validation applied by all providers before returning data."""
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Provider {self.name} missing columns: {missing}")

        if len(df) < 50:
            raise ValueError(
                f"Insufficient data: got {len(df)} bars for {request.symbol} "
                f"({request.timeframe}). Need at least 50."
            )

        df = df.sort_index()
        df = df[list(required)].astype(float)
        df.index.name = "datetime"
        return df
