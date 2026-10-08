from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Determine sync and async database URLs
sync_db_url = settings.DATABASE_URL
async_db_url = settings.ASYNC_DATABASE_URL

# Handle SQLite connect args if sqlite is used
sync_args = {"check_same_thread": False} if "sqlite" in sync_db_url else {}
async_args = {"check_same_thread": False} if "sqlite" in async_db_url else {}

# Engines
sync_engine = create_engine(sync_db_url, echo=False, connect_args=sync_args)
async_engine = create_async_engine(async_db_url, echo=False, connect_args=async_args)

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
