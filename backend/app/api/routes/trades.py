"""
Paper trading API routes.

Endpoints:
  POST   /api/v1/trades              — open a new trade
  GET    /api/v1/trades              — list all trades (open + closed)
  PUT    /api/v1/trades/{id}/close   — manually close a trade
  GET    /api/v1/portfolio           — account summary + open positions + performance
  DELETE /api/v1/account/reset       — wipe all trades, reset capital to $1M
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.trade import (
    OpenTradeRequest, TradeResponse, AccountResponse,
    PerformanceResponse, PortfolioResponse,
)
from app.models.trade import Account, Trade
from app.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["trades"])

POSITION_SIZE   = 100_000.0   # USD per trade
STARTING_CAPITAL = 1_000_000.0
MAX_TRADE_DAYS  = 60          # auto-close after 60 days


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_account(session: AsyncSession) -> Account:
    result = await session.execute(select(Account).where(Account.id == 1))
    account = result.scalar_one_or_none()
    if account is None:
        account = Account(
            id=1,
            starting_capital=STARTING_CAPITAL,
            realized_pnl=0.0,
            reset_at=datetime.now(timezone.utc),
        )
        session.add(account)
        await session.flush()
    return account


def _fetch_current_price(symbol: str) -> Optional[float]:
    """Get latest close price via TradingView → yfinance fallback."""
    try:
        from app.data.providers.tradingview_provider import TradingViewProvider
        from app.data.providers.base import DataRequest
        df = TradingViewProvider().get_ohlcv(DataRequest(symbol=symbol, timeframe="1D", bars=60))
        return float(df["close"].iloc[-1])
    except Exception:
        pass
    try:
        from app.data.providers.yfinance_provider import YFinanceProvider
        from app.data.providers.base import DataRequest
        from app.api.routes.analysis import SYMBOL_ALIASES
        yf_sym = SYMBOL_ALIASES.get(symbol.upper(), symbol)
        df = YFinanceProvider().get_ohlcv(DataRequest(symbol=yf_sym, timeframe="1D", bars=60))
        return float(df["close"].iloc[-1])
    except Exception as e:
        logger.warning("Could not fetch price for %s: %s", symbol, e)
        return None


def _calc_pnl(direction: str, entry: float, current: float, size: float):
    if direction == "long":
        pct = (current - entry) / entry
    else:
        pct = (entry - current) / entry
    return round(pct * size, 2), round(pct * 100, 4)


def _trade_to_response(trade: Trade, current_price: Optional[float] = None) -> TradeResponse:
    now = datetime.now(timezone.utc)
    entry_time = trade.entry_time
    if entry_time.tzinfo is None:
        entry_time = entry_time.replace(tzinfo=timezone.utc)

    duration_h = (now - entry_time).total_seconds() / 3600 if trade.is_open else None

    unreal_usd = unreal_pct = None
    if trade.is_open and current_price:
        unreal_usd, unreal_pct = _calc_pnl(
            trade.direction, trade.entry_price, current_price, trade.position_size
        )

    return TradeResponse(
        id=trade.id,
        symbol=trade.symbol,
        timeframe=trade.timeframe,
        direction=trade.direction,
        position_size=trade.position_size,
        entry_price=trade.entry_price,
        entry_time=entry_time,
        exit_price=trade.exit_price,
        exit_time=trade.exit_time,
        close_reason=trade.close_reason,
        pnl_usd=trade.pnl_usd,
        pnl_pct=trade.pnl_pct,
        is_open=trade.is_open,
        current_price=current_price if trade.is_open else None,
        unrealized_pnl_usd=unreal_usd,
        unrealized_pnl_pct=unreal_pct,
        duration_hours=round(duration_h, 1) if duration_h is not None else None,
    )


async def _build_account_response(
    session: AsyncSession,
    account: Account,
    open_trades: list[Trade],
) -> AccountResponse:
    total_capital = account.starting_capital + account.realized_pnl
    allocated     = len(open_trades) * POSITION_SIZE
    available     = total_capital - allocated

    # Unrealized P&L across all open positions
    unrealized = 0.0
    for t in open_trades:
        price = _fetch_current_price(t.symbol)
        if price:
            u, _ = _calc_pnl(t.direction, t.entry_price, price, t.position_size)
            unrealized += u

    max_pos = int(total_capital // POSITION_SIZE)

    reset_at = account.reset_at
    if reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)

    return AccountResponse(
        starting_capital=account.starting_capital,
        realized_pnl=round(account.realized_pnl, 2),
        total_capital=round(total_capital, 2),
        allocated_capital=round(allocated, 2),
        available_capital=round(available, 2),
        unrealized_pnl=round(unrealized, 2),
        net_equity=round(total_capital + unrealized, 2),
        open_count=len(open_trades),
        max_positions=max_pos,
        can_open=available >= POSITION_SIZE,
        reset_at=reset_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/trades", response_model=TradeResponse, status_code=201)
async def open_trade(req: OpenTradeRequest, session: AsyncSession = Depends(get_session)):
    """Open a new $100K paper trade."""
    if req.direction not in ("long", "short"):
        raise HTTPException(status_code=400, detail="direction must be 'long' or 'short'")

    account = await _get_or_create_account(session)
    total_capital = account.starting_capital + account.realized_pnl

    # Count open trades
    result = await session.execute(select(func.count()).where(Trade.is_open == True))
    open_count = result.scalar_one()
    allocated = open_count * POSITION_SIZE

    if total_capital - allocated < POSITION_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Yetersiz sermaye. Müsait: ${total_capital - allocated:,.0f}"
        )

    # Fetch entry price
    symbol = req.symbol.upper().strip()
    entry_price = _fetch_current_price(symbol)
    if entry_price is None:
        raise HTTPException(status_code=502, detail=f"Fiyat alınamadı: {symbol}")

    trade = Trade(
        symbol=symbol,
        timeframe=req.timeframe,
        direction=req.direction,
        position_size=POSITION_SIZE,
        entry_price=entry_price,
        entry_time=datetime.now(timezone.utc),
        is_open=True,
    )
    session.add(trade)
    await session.commit()
    await session.refresh(trade)

    logger.info("Trade opened: %s %s %s @ %.4f", trade.id, symbol, req.direction, entry_price)
    return _trade_to_response(trade, entry_price)


@router.get("/trades", response_model=list[TradeResponse])
async def list_trades(
    status: Optional[str] = None,   # "open" | "closed" | None = all
    session: AsyncSession = Depends(get_session),
):
    """List trades. status=open|closed or omit for all."""
    q = select(Trade).order_by(Trade.entry_time.desc())
    if status == "open":
        q = q.where(Trade.is_open == True)
    elif status == "closed":
        q = q.where(Trade.is_open == False)

    result = await session.execute(q)
    trades = result.scalars().all()

    responses = []
    for t in trades:
        price = _fetch_current_price(t.symbol) if t.is_open else None
        responses.append(_trade_to_response(t, price))
    return responses


@router.put("/trades/{trade_id}/close", response_model=TradeResponse)
async def close_trade(trade_id: int, session: AsyncSession = Depends(get_session)):
    """Manually close an open trade."""
    result = await session.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()

    if trade is None:
        raise HTTPException(status_code=404, detail="Trade bulunamadı")
    if not trade.is_open:
        raise HTTPException(status_code=400, detail="Trade zaten kapalı")

    exit_price = _fetch_current_price(trade.symbol)
    if exit_price is None:
        raise HTTPException(status_code=502, detail=f"Çıkış fiyatı alınamadı: {trade.symbol}")

    pnl_usd, pnl_pct = _calc_pnl(trade.direction, trade.entry_price, exit_price, trade.position_size)

    trade.exit_price   = exit_price
    trade.exit_time    = datetime.now(timezone.utc)
    trade.close_reason = "manual"
    trade.pnl_usd      = pnl_usd
    trade.pnl_pct      = pnl_pct
    trade.is_open      = False

    # Update account realized P&L
    account = await _get_or_create_account(session)
    account.realized_pnl += pnl_usd

    await session.commit()
    await session.refresh(trade)

    logger.info("Trade closed: %s %s manual P&L=%.2f", trade_id, trade.symbol, pnl_usd)
    return _trade_to_response(trade)


@router.get("/portfolio", response_model=PortfolioResponse)
async def get_portfolio(session: AsyncSession = Depends(get_session)):
    """Full portfolio: account summary + open positions + performance stats."""
    account = await _get_or_create_account(session)

    # Open trades
    open_result = await session.execute(select(Trade).where(Trade.is_open == True).order_by(Trade.entry_time.desc()))
    open_trades = open_result.scalars().all()

    # All closed trades
    closed_result = await session.execute(select(Trade).where(Trade.is_open == False))
    closed_trades = closed_result.scalars().all()

    # Account response (fetches live prices internally)
    account_resp = await _build_account_response(session, account, list(open_trades))

    # Open trade responses with live prices
    open_responses = []
    for t in open_trades:
        price = _fetch_current_price(t.symbol)
        open_responses.append(_trade_to_response(t, price))

    # Performance
    total_trades  = len(open_trades) + len(closed_trades)
    winning       = [t for t in closed_trades if (t.pnl_usd or 0) > 0]
    losing        = [t for t in closed_trades if (t.pnl_usd or 0) <= 0]
    pnl_values    = [t.pnl_usd for t in closed_trades if t.pnl_usd is not None]
    total_pnl     = sum(pnl_values)
    win_rate      = len(winning) / len(closed_trades) * 100 if closed_trades else 0.0

    perf = PerformanceResponse(
        total_trades=total_trades,
        open_trades=len(open_trades),
        closed_trades=len(closed_trades),
        winning_trades=len(winning),
        losing_trades=len(losing),
        win_rate=round(win_rate, 1),
        total_pnl_usd=round(total_pnl, 2),
        avg_pnl_usd=round(total_pnl / len(closed_trades), 2) if closed_trades else 0.0,
        best_trade_usd=round(max(pnl_values), 2) if pnl_values else 0.0,
        worst_trade_usd=round(min(pnl_values), 2) if pnl_values else 0.0,
        total_return_pct=round(total_pnl / account.starting_capital * 100, 2),
    )

    return PortfolioResponse(
        account=account_resp,
        open_trades=open_responses,
        performance=perf,
    )


@router.delete("/account/reset", status_code=200)
async def reset_account(session: AsyncSession = Depends(get_session)):
    """Delete all trades and reset capital to $1M."""
    await session.execute(Trade.__table__.delete())
    account = await _get_or_create_account(session)
    account.realized_pnl = 0.0
    account.reset_at     = datetime.now(timezone.utc)
    await session.commit()
    logger.info("Account reset to $1M")
    return {"message": "Hesap sıfırlandı. Sermaye: $1,000,000"}
