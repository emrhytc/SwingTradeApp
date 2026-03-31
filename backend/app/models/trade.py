"""
SQLAlchemy models for paper trading.
Two tables:
  - account: single row tracking capital ($1M start, updated by closed trades)
  - trades:  every paper trade opened/closed by the user
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "account"

    id                = Column(Integer, primary_key=True, default=1)
    starting_capital  = Column(Float, nullable=False, default=1_000_000.0)
    realized_pnl      = Column(Float, nullable=False, default=0.0)
    reset_at          = Column(DateTime, nullable=False,
                               default=lambda: datetime.now(timezone.utc))


class Trade(Base):
    __tablename__ = "trades"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    symbol        = Column(String(32), nullable=False)
    timeframe     = Column(String(8),  nullable=False)
    direction     = Column(String(8),  nullable=False)   # "long" | "short"
    position_size = Column(Float, nullable=False, default=100_000.0)

    entry_price   = Column(Float, nullable=False)
    entry_time    = Column(DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    exit_price    = Column(Float,   nullable=True)
    exit_time     = Column(DateTime, nullable=True)
    close_reason  = Column(String(16), nullable=True)  # "manual" | "expired"

    pnl_usd       = Column(Float, nullable=True)
    pnl_pct       = Column(Float, nullable=True)

    is_open       = Column(Boolean, nullable=False, default=True)
