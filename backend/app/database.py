"""
Viva — Async Database Engine and Session Factory
Uses SQLAlchemy 2.x async + asyncpg driver + pgvector type registration.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine — created once at module level, reused across all requests.
# pool_pre_ping=True drops stale connections silently (important for Supabase
# which has idle connection timeouts on the free tier).
# ---------------------------------------------------------------------------
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=1,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=300,
    # NOTE: If migrating to Supabase transaction-mode pooler (port 6543),
    # also pass: connect_args={"prepared_statement_cache_size": 0}
    # and use the pooler URI. Verify with the project owner before changing.
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Context-manager that yields a session and commits or rolls back on exit.
    Use as a dependency in FastAPI routes via Depends(get_db).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a DB session per request."""
    async with get_db_session() as session:
        yield session
