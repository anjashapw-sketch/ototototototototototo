"""
SQLite async engine setup using
SQLAlchemy 2.0 with aiosqlite.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from bot.config import settings


# ━━━ ENGINE ━━━
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    }
)

# ━━━ SESSION MAKER ━━━
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)


@asynccontextmanager
async def get_session() -> (
    AsyncGenerator[AsyncSession, None]
):
    """
    Context manager for database sessions.
    Auto-commits on success, rolls back
    on exception.

    Usage:
        async with get_session() as session:
            result = await session.execute(...)
    """
    session = async_session_maker()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()