"""
Pydantic schemas for paper trading API.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── Requests ──────────────────────────────────────────────────────────────────

class OpenTradeRequest(BaseModel):
    symbol:    str = Field(..., description="e.g. AAPL, NQ1!, XAUUSD")
    timeframe: str = Field("1D", description="15m | 1H | 4H | 1D | 1W")
    direction: str = Field(..., description="long | short")


class CloseTradeRequest(BaseModel):
    trade_id: int


# ── Responses ─────────────────────────────────────────────────────────────────

class TradeResponse(BaseModel):
    id:            int
    symbol:        str
    timeframe:     str
    direction:     str
    position_size: float

    entry_price:   float
    entry_time:    datetime

    exit_price:    Optional[float] = None
    exit_time:     Optional[datetime] = None
    close_reason:  Optional[str] = None

    pnl_usd:       Optional[float] = None
    pnl_pct:       Optional[float] = None
    is_open:       bool

    # Computed live fields (only for open trades)
    current_price:      Optional[float] = None
    unrealized_pnl_usd: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    duration_hours:     Optional[float] = None

    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    starting_capital:  float
    realized_pnl:      float
    total_capital:     float   # starting_capital + realized_pnl
    allocated_capital: float   # open_count × 100K
    available_capital: float   # total_capital - allocated_capital
    unrealized_pnl:    float   # sum of live P&L of open positions
    net_equity:        float   # total_capital + unrealized_pnl
    open_count:        int
    max_positions:     int     # floor(total_capital / 100K)
    can_open:          bool    # available_capital >= 100K
    reset_at:          datetime


class PerformanceResponse(BaseModel):
    total_trades:     int
    open_trades:      int
    closed_trades:    int
    winning_trades:   int
    losing_trades:    int
    win_rate:         float    # %
    total_pnl_usd:    float    # realized only
    avg_pnl_usd:      float
    best_trade_usd:   float
    worst_trade_usd:  float
    total_return_pct: float    # vs starting capital


class PortfolioResponse(BaseModel):
    account:      AccountResponse
    open_trades:  List[TradeResponse]
    performance:  PerformanceResponse
