"""
yfinance implementation of MarketDataProvider.
For 4H data, resamples from 1H since yfinance free tier does not support 4h directly.
"""
import pandas as pd
import yfinance as yf
import logging
from .base import MarketDataProvider, DataRequest

logger = logging.getLogger(__name__)

# Map our internal timeframe codes to yfinance interval strings
_TIMEFRAME_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "4H": "1h",  # We fetch 1H and resample to 4H
    "1D": "1d",
    "1W": "1wk",
}

# How many bars to fetch from yfinance to cover our target bar count
# (4H requires 4x 1H bars)
_FETCH_MULTIPLIER = {
    "4H": 4,
}

# yfinance period strings for bar count approximations
_PERIOD_FOR_BARS = {
    "1m": "7d",
    "5m": "60d",
    "15m": "60d",
    "30m": "60d",
    "1h": "730d",
    "1d": "max",
    "1wk": "max",
}


class YFinanceProvider(MarketDataProvider):

    @property
    def name(self) -> str:
        return "yfinance"

    def supports_timeframe(self, timeframe: str) -> bool:
        return timeframe in _TIMEFRAME_MAP

    def get_ohlcv(self, request: DataRequest) -> pd.DataFrame:
        if not self.supports_timeframe(request.timeframe):
            raise ValueError(f"yfinance provider does not support timeframe: {request.timeframe}")

        yf_interval = _TIMEFRAME_MAP[request.timeframe]
        need_resample = request.timeframe == "4H"

        fetch_bars = request.bars * _FETCH_MULTIPLIER.get(request.timeframe, 1) + 50
        period = _PERIOD_FOR_BARS.get(yf_interval, "max")

        logger.info(
            "Fetching %s %s (yf_interval=%s, period=%s, need_resample=%s)",
            request.symbol, request.timeframe, yf_interval, period, need_resample,
        )

        ticker = yf.Ticker(request.symbol)
        raw = ticker.history(period=period, interval=yf_interval, auto_adjust=True)

        if raw.empty:
            raise ValueError(f"No data returned from yfinance for symbol: {request.symbol}")

        df = raw.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })

        # Normalize timezone to UTC-naive for consistent handling
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)

        df = df[["open", "high", "low", "close", "volume"]]

        if need_resample:
            df = self._resample_to_4h(df)

        # Keep only the last N bars
        df = df.tail(request.bars)

        return self.validate_dataframe(df, request)

    def _resample_to_4h(self, df: pd.DataFrame) -> pd.DataFrame:
        """Resample 1H OHLCV dataframe to 4H bars."""
        resampled = df.resample("4h", closed="left", label="left").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna()
        return resampled
