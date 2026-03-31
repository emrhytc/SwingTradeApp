"""
TradingView data provider via unofficial WebSocket API.
Supports TradingView native symbol notation: NQ1!, XAUUSD, GC1!, ES1!, etc.

Symbol formats accepted:
  - Plain:          NQ1!, XAUUSD, AAPL, BTC-USD
  - With exchange:  NQ1!:CME, XAUUSD:OANDA

Exchange is auto-detected for common symbols. Unknown symbols fall back
to yfinance automatically (see analysis.py _get_provider logic).
"""
import json
import re
import random
import string
import logging
from datetime import datetime, timezone

import pandas as pd
import websocket

from .base import MarketDataProvider, DataRequest

logger = logging.getLogger(__name__)

# TradingView resolution strings
_TIMEFRAME_MAP = {
    "1m":  "1",
    "5m":  "5",
    "15m": "15",
    "30m": "30",
    "1H":  "60",
    "4H":  "240",
    "1D":  "D",
    "1W":  "W",
}

# Default exchange for known symbols. Users can override with SYMBOL:EXCHANGE notation.
_EXCHANGE_MAP: dict[str, str] = {
    # Index futures (CME/CBOT)
    "NQ1!": "CME",   "NQ!1": "CME",
    "ES1!": "CME",   "ES!1": "CME",
    "RTY1!": "CME",  "RTY!1": "CME",
    "YM1!": "CBOT",  "YM!1": "CBOT",
    # Energy futures
    "CL1!": "NYMEX", "CL!1": "NYMEX",
    "NG1!": "NYMEX", "NG!1": "NYMEX",
    # Metals futures
    "GC1!": "COMEX", "GC!1": "COMEX",
    "SI1!": "COMEX", "SI!1": "COMEX",
    # Forex / spot metals (OANDA)
    "XAUUSD": "OANDA", "XAGUSD": "OANDA",
    "EURUSD": "FX",    "GBPUSD": "FX",
    "USDJPY": "FX",    "AUDUSD": "FX",
    "USDCAD": "FX",    "USDCHF": "FX",
    "NZDUSD": "FX",    "USDTRY": "FX",
    # Crypto (Binance, common pairs)
    "BTCUSDT": "BINANCE", "ETHUSDT": "BINANCE",
    "SOLUSDT": "BINANCE", "BNBUSDT": "BINANCE",
    # US mega-cap stocks
    "AAPL": "NASDAQ", "MSFT": "NASDAQ", "NVDA": "NASDAQ",
    "TSLA": "NASDAQ", "AMZN": "NASDAQ", "GOOG": "NASDAQ",
    "GOOGL": "NASDAQ", "META": "NASDAQ", "NFLX": "NASDAQ",
    "INTC": "NASDAQ", "AMD": "NASDAQ",  "QCOM": "NASDAQ",
    # US ETFs
    "SPY": "AMEX",    "QQQ": "NASDAQ",  "IWM": "AMEX",
    "GLD": "NYSE",    "SLV": "NYSE",    "TLT": "NASDAQ",
    "XLF": "NYSE",    "XLE": "NYSE",    "XLK": "NYSE",
    # Indices
    "SPX": "SP",      "NDX": "NASDAQ",  "DJI": "DJ",
    "VIX": "CBOE",
}

_TV_WS_URL = (
    "wss://data.tradingview.com/socket.io/websocket"
    "?from=chart%2F&date=&type=chart"
)
_TV_HEADERS = {"Origin": "https://data.tradingview.com"}
_RECV_TIMEOUT = 10  # seconds per recv() call
_MAX_ITERATIONS = 200


def _rand_session(n: int = 12) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


def _pack(msg: str) -> str:
    """Wrap a JSON string in TradingView's wire format."""
    return f"~m~{len(msg)}~m~{msg}"


def _send(ws: websocket.WebSocket, method: str, params: list) -> None:
    payload = json.dumps({"m": method, "p": params}, separators=(",", ":"))
    ws.send(_pack(payload))


def _parse_packets(raw: str) -> list[dict]:
    """Extract all JSON objects from a raw TradingView WebSocket frame."""
    return [json.loads(m) for m in re.findall(r"~m~\d+~m~(\{.+?\})(?=~m~|$)", raw, re.DOTALL)]


def _resolve_symbol_exchange(symbol: str) -> tuple[str, str]:
    """
    Split 'SYMBOL:EXCHANGE' or look up exchange from the map.
    Returns (symbol, exchange).
    """
    if ":" in symbol:
        parts = symbol.split(":", 1)
        return parts[0].upper(), parts[1].upper()
    upper = symbol.upper()
    exchange = _EXCHANGE_MAP.get(upper, "")
    return upper, exchange


class TradingViewProvider(MarketDataProvider):
    """Fetches OHLCV data from TradingView via WebSocket."""

    @property
    def name(self) -> str:
        return "tradingview"

    def supports_timeframe(self, timeframe: str) -> bool:
        return timeframe in _TIMEFRAME_MAP

    def get_ohlcv(self, request: DataRequest) -> pd.DataFrame:
        if not self.supports_timeframe(request.timeframe):
            raise ValueError(f"TradingView provider does not support timeframe: {request.timeframe}")

        tv_symbol, exchange = _resolve_symbol_exchange(request.symbol)
        tv_tf = _TIMEFRAME_MAP[request.timeframe]

        logger.info(
            "TradingView fetch: symbol=%s exchange=%s tf=%s bars=%d",
            tv_symbol, exchange or "(auto)", tv_tf, request.bars,
        )

        raw_bars = self._fetch_via_websocket(tv_symbol, exchange, tv_tf, request.bars)

        if not raw_bars:
            raise ValueError(
                f"No data returned from TradingView for {tv_symbol} "
                f"(exchange={exchange or 'auto'}, tf={request.timeframe}). "
                "Try specifying exchange explicitly: SYMBOL:EXCHANGE (e.g. NQ1!:CME)"
            )

        df = pd.DataFrame(raw_bars)
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df = df.set_index("datetime").tz_localize(None)
        df = df[["open", "high", "low", "close", "volume"]]
        df = df.sort_index()

        return self.validate_dataframe(df, request)

    def _fetch_via_websocket(
        self, symbol: str, exchange: str, tv_tf: str, bars: int
    ) -> list[dict]:
        chart_session = f"cs_{_rand_session()}"
        bars_data: list[dict] = []
        completed = False

        try:
            ws = websocket.create_connection(
                _TV_WS_URL,
                headers=_TV_HEADERS,
                timeout=_RECV_TIMEOUT,
            )
        except Exception as e:
            raise RuntimeError(f"TradingView WebSocket connection failed: {e}")

        try:
            _send(ws, "set_auth_token", ["unauthorized_user_token"])
            _send(ws, "chart_create_session", [chart_session, ""])

            # Build symbol descriptor
            sym_descriptor: dict = {"symbol": symbol, "adjustment": "splits"}
            if exchange:
                sym_descriptor["exchange"] = exchange
            _send(ws, "resolve_symbol", [
                chart_session, "sds_sym_1",
                f"={json.dumps(sym_descriptor, separators=(',', ':'))}",
            ])
            _send(ws, "create_series", [
                chart_session, "sds_1", "s1", "sds_sym_1", tv_tf, bars, "",
            ])

            for _ in range(_MAX_ITERATIONS):
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    logger.warning("TradingView recv timeout for %s", symbol)
                    break

                # Respond to heartbeat pings
                for hb in re.findall(r"~h~(\d+)", raw):
                    ws.send(_pack(f"~h~{hb}"))

                for packet in _parse_packets(raw):
                    m = packet.get("m", "")

                    if m == "symbol_error":
                        err = packet.get("p", ["", "", "unknown error"])
                        raise ValueError(
                            f"TradingView symbol_error for {symbol}: {err[-1]}"
                        )

                    if m == "timescale_update":
                        try:
                            series = packet["p"][1]["sds_1"]["s"]
                            for bar in series:
                                v = bar["v"]
                                bars_data.append({
                                    "timestamp": v[0],
                                    "open":      v[1],
                                    "high":      v[2],
                                    "low":       v[3],
                                    "close":     v[4],
                                    "volume":    v[5] if len(v) > 5 else 0.0,
                                })
                        except (KeyError, IndexError):
                            pass

                    if m == "series_completed":
                        completed = True

                if completed:
                    break

        finally:
            try:
                ws.close()
            except Exception:
                pass

        if not completed:
            logger.warning(
                "TradingView series_completed not received for %s — returning %d bars collected",
                symbol, len(bars_data),
            )

        return bars_data
