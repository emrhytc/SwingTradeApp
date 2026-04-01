"""
Async SQLAlchemy engine + session factory.

DATABASE_URL controls which backend is used:
  sqlite+aiosqlite:///./swingtrader.db  → local development
  postgresql+asyncpg://user:pass@host/db → Render PostgreSQL (production)

The correct async driver is chosen automatically from the URL scheme.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings

# Render supplies postgres:// URLs; SQLAlchemy needs postgresql+asyncpg://
def _normalise_url(url: str) -> str:
    # Render supplies postgres:// or postgresql:// — both need asyncpg driver
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

_db_url = _normalise_url(settings.DATABASE_URL)

# PostgreSQL needs pool_pre_ping; SQLite doesn't support it but ignores it
engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
