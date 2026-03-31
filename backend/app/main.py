import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.api.routes.trades import router as trades_router, POSITION_SIZE, MAX_TRADE_DAYS, _fetch_current_price, _calc_pnl
from app.db import engine, AsyncSessionLocal
from app.models.trade import Base, Account, Trade

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def _auto_close_expired_trades():
    """Background task: close trades older than MAX_TRADE_DAYS every hour."""
    while True:
        await asyncio.sleep(3600)  # run every hour
        try:
            async with AsyncSessionLocal() as session:
                cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_TRADE_DAYS)
                result = await session.execute(
                    select(Trade).where(Trade.is_open == True)
                )
                open_trades = result.scalars().all()

                expired = []
                for t in open_trades:
                    entry_time = t.entry_time
                    if entry_time.tzinfo is None:
                        entry_time = entry_time.replace(tzinfo=timezone.utc)
                    if entry_time <= cutoff:
                        expired.append(t)

                if not expired:
                    continue

                # Get account
                acc_result = await session.execute(select(Account).where(Account.id == 1))
                account = acc_result.scalar_one_or_none()

                for t in expired:
                    exit_price = _fetch_current_price(t.symbol)
                    if exit_price is None:
                        exit_price = t.entry_price  # fallback: close at entry (no P&L)
                    pnl_usd, pnl_pct = _calc_pnl(
                        t.direction, t.entry_price, exit_price, t.position_size
                    )
                    t.exit_price   = exit_price
                    t.exit_time    = datetime.now(timezone.utc)
                    t.close_reason = "expired"
                    t.pnl_usd      = pnl_usd
                    t.pnl_pct      = pnl_pct
                    t.is_open      = False
                    if account:
                        account.realized_pnl += pnl_usd
                    logger.info("Auto-closed expired trade %s %s P&L=%.2f", t.id, t.symbol, pnl_usd)

                await session.commit()
        except Exception as e:
            logger.error("Auto-close task error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SwingTradeApp API starting up (env=%s)", settings.APP_ENV)

    # Create all DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure account row exists
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Account).where(Account.id == 1))
        if result.scalar_one_or_none() is None:
            session.add(Account(
                id=1,
                starting_capital=1_000_000.0,
                realized_pnl=0.0,
                reset_at=datetime.now(timezone.utc),
            ))
            await session.commit()
            logger.info("Account initialized with $1,000,000 starting capital")

    # Start background auto-close task
    task = asyncio.create_task(_auto_close_expired_trades())

    yield

    task.cancel()
    logger.info("SwingTradeApp API shutting down")


app = FastAPI(
    title="SwingTradeApp API",
    description="Market environment suitability engine for swing trading.",
    version="0.1.0",
    lifespan=lifespan,
)

_cors_origins = settings.get_cors_origins()
_allow_credentials = "*" not in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analysis_router)
app.include_router(trades_router)
