"""
db.py — Database engine, session factory, and table initialisation.

We use SQLAlchemy 2.0 async engine backed by aiosqlite.
Call `init_db()` once at startup to create all tables.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.config import get_settings
from backend.app.models import Base

_settings = get_settings()

# Create a single engine for the application lifetime.
# echo=False keeps SQL out of production logs.
engine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
)

# Session factory — use as an async context manager.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables if they do not already exist.

    Safe to call multiple times (CREATE TABLE IF NOT EXISTS semantics).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
