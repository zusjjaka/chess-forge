import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from db.base import Base
from db.session import get_db_session
from main import app
from models.refresh_token import RefreshToken
from models.user import User

TEST_DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5432/auth_test'

engine = create_async_engine(TEST_DATABASE_URL)

TestSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope='session', autouse=True)
async def setup_database():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def session():
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


TEST_DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5432/auth_test'

engine = create_async_engine(TEST_DATABASE_URL)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def db_session():
    async with SessionFactory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_database():
    yield

    async with SessionFactory() as session:
        await session.execute(delete(RefreshToken))
        await session.execute(delete(User))
        await session.commit()
