import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

TEST_DATABASE_URL = (
    'postgresql+asyncpg://training_test:root@localhost:5432/'
    'training_test'
)

TEST_PUBLIC_KEY_PATH = (
    Path(__file__).parent.parent / 'keys' / 'public_key.pem'
)

os.environ['DATABASE__URL'] = TEST_DATABASE_URL
os.environ['REPERTOIRE_SERVICE__HOST'] = '127.0.0.1'
os.environ['REPERTOIRE_SERVICE__PORT'] = '50051'
os.environ['REPERTOIRE_SERVICE__TIMEOUT'] = '1.0'
os.environ['JWT__PUBLIC_KEY_PATH'] = str(TEST_PUBLIC_KEY_PATH)

from db.base import Base
from api.dependencies import (
    get_current_user_id,
    get_repertoire_client,
    get_training_service,
)
from main import app
from models.session import TrainingSession
from models.stat import LineTrainingStats
from grpc_client.models import TrainingLine, TrainingTree


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def repertoire_id() -> UUID:
    return uuid4()


@pytest.fixture
def root_line_id() -> UUID:
    return uuid4()


@pytest.fixture
def child_line_id() -> UUID:
    return uuid4()


@pytest.fixture
def training_tree(
    root_line_id: UUID,
    child_line_id: UUID,
) -> TrainingTree:
    return TrainingTree(
        repertoire_revision=1,
        lines=[
            TrainingLine(
                id=root_line_id,
                parent_id=None,
                tag='root',
                moves=['e2e4'],
                analytic_version=1,
            ),
            TrainingLine(
                id=child_line_id,
                parent_id=root_line_id,
                tag='main',
                moves=['e7e5'],
                analytic_version=1,
            ),
        ],
    )


@dataclass
class FakeRepertoireClient:
    tree: TrainingTree
    revision: int | None = None

    async def get_training_tree(
        self,
        user_id: UUID,
        repertoire_id: UUID,
        start_line_id: UUID | None,
    ) -> TrainingTree:
        return self.tree

    async def get_repertoire_revision(
        self,
        user_id: UUID,
        repertoire_id: UUID,
    ) -> int:
        if self.revision is not None:
            return self.revision

        return self.tree.repertoire_revision

    async def close(self) -> None:
        return None


@pytest.fixture
def fake_repertoire_client(
    training_tree: TrainingTree,
) -> FakeRepertoireClient:
    return FakeRepertoireClient(tree=training_tree)


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(
        TEST_DATABASE_URL
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def api_client(
    session: AsyncSession,
    fake_repertoire_client: FakeRepertoireClient,
    user_id: UUID,
) -> AsyncGenerator[AsyncClient]:
    async def override_db_session():
        yield session

    def override_current_user_id() -> UUID:
        return user_id

    def override_repertoire_client() -> FakeRepertoireClient:
        return fake_repertoire_client

    app.dependency_overrides[get_current_user_id] = (
        override_current_user_id
    )
    app.dependency_overrides[get_repertoire_client] = (
        override_repertoire_client
    )

    from db.session import get_db_session

    app.dependency_overrides[get_db_session] = (
        override_db_session
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_api_client(
    session: AsyncSession,
    fake_repertoire_client: FakeRepertoireClient,
) -> AsyncGenerator[AsyncClient]:
    from db.session import get_db_session

    async def override_db_session():
        yield session

    def override_repertoire_client() -> FakeRepertoireClient:
        return fake_repertoire_client

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_repertoire_client] = (
        override_repertoire_client
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def make_training_session():
    def factory(
        *,
        user_id: UUID,
        repertoire_id: UUID,
        start_line_id: UUID,
        selected_moves: list[str],
        selected_path: list[dict],
        repertoire_revision: int = 1,
        current_ply: int = 0,
        status='active',
    ) -> TrainingSession:
        return TrainingSession(
            user_id=user_id,
            repertoire_id=repertoire_id,
            start_line_id=start_line_id,
            current_ply=current_ply,
            repertoire_revision=repertoire_revision,
            selected_moves=selected_moves,
            selected_path=selected_path,
            status=status,
        )

    return factory


@pytest.fixture
def make_stat():
    def factory(
        *,
        user_id: UUID,
        line_id: UUID,
        line_analytic_version: int = 1,
        attempts: int = 0,
        fails: int = 0,
        consecutive_successes: int = 0,
        consecutive_failures: int = 0,
        target_interval: int = 1,
    ) -> LineTrainingStats:
        return LineTrainingStats(
            user_id=user_id,
            line_id=line_id,
            line_analytic_version=line_analytic_version,
            attempts=attempts,
            fails=fails,
            consecutive_successes=consecutive_successes,
            consecutive_failures=consecutive_failures,
            target_interval=target_interval,
        )

    return factory
