from app.db.session import async_engine
from app.models.base import Base

# Import all models so metadata is populated
import app.models  # noqa: F401


async def init_models() -> None:
    """Create all tables in the database asynchronously if they don't already exist."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
