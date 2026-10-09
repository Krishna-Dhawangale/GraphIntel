from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings
from app.db.urls import normalize_postgres_driver

# Determine sync and async database URLs
sync_db_url = normalize_postgres_driver(settings.DATABASE_URL, "psycopg2")
async_db_url = normalize_postgres_driver(settings.ASYNC_DATABASE_URL, "asyncpg")

# Handle connect args
sync_args = {"check_same_thread": False} if "sqlite" in sync_db_url else {}
if "sqlite" in async_db_url:
    async_args = {"check_same_thread": False}
elif "asyncpg" in async_db_url:
    async_args = {"statement_cache_size": 0}
else:
    async_args = {}

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
