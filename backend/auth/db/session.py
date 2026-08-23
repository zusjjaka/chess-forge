from collections.abc import AsyncGenerator

from core.config import get_settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

settings = get_settings()

engine: AsyncEngine = create_async_engine(url=settings.database_url, pool_pre_ping=True)

AsyncSessionFactory = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session
