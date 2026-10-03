from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from repositories.session import TrainingSessionRepository
from repositories.stat import LineTrainingStatsRepository
from schemas.session import TrainingSessionCreate
from exceptions import (
    TrainingSessionInvalidatedError,
    TrainingSessionNotActiveError,
    TrainingSessionNotFoundError,
)
from grpc_client.models import TrainingLine, TrainingTree
from models.session import TrainingSession, TrainingSessionStatus
from services.training import TrainingService


class FakeSessionRepository:
    def __init__(self):
        self.session = None
        self.added = []

    async def get(
        self,
        session_id,
        user_id,
        for_update=False,
    ):
        return self.session

    async def add(self, session):
        self.added.append(session)


class FakeStatsRepository:
    def __init__(self):
        self.stats = []
        self.successes = []
        self.failures = []

    async def get_many(self, user_id, line_keys):
        return self.stats

    async def increment_success(
        self,
        user_id,
        line_id,
        line_analytic_version,
    ):
        self.successes.append(
            (
                user_id,
                line_id,
                line_analytic_version,
            )
        )

    async def increment_failure(
        self,
        user_id,
        line_id,
        line_analytic_version,
    ):
        self.failures.append(
            (
                user_id,
                line_id,
                line_analytic_version,
            )
        )


class FakeSelector:
    def __init__(self, selected):
        self.selected = selected
        self.calls = []

    def select(self, lines, stats):
        self.calls.append((lines, stats))
        return self.selected


class FakeRepertoireClient:
    def __init__(
        self,
        tree,
        revision=None,
    ):
        self.tree = tree
        self.revision = revision

    async def get_training_tree(
        self,
        user_id,
        repertoire_id,
        start_line_id,
    ):
        return self.tree

    async def get_repertoire_revision(
        self,
        user_id,
        repertoire_id,
    ):
        return (
            self.tree.repertoire_revision
            if self.revision is None
            else self.revision
        )


class FakeDBSession:
    def __init__(self):
        self.commit_count = 0
        self.refresh_count = 0
        self.rollback_count = 0

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, instance):
        self.refresh_count += 1

    async def rollback(self):
        self.rollback_count += 1


@pytest.fixture
def service():
    service = object.__new__(TrainingService)

    service._session = cast(AsyncSession, FakeDBSession())
    service._session_repository = cast(
        TrainingSessionRepository,
        FakeSessionRepository(),
    )
    service._stats_repository = cast(
        LineTrainingStatsRepository,
        FakeStatsRepository(),
    )

    return service


@pytest.mark.asyncio
async def test_get_session_not_found(service):
    session_repository = service._session_repository

    with pytest.raises(TrainingSessionNotFoundError):
        await service.get_session(
            uuid4(),
            uuid4(),
        )


@pytest.mark.asyncio
async def test_get_session_returns_session(service):
    expected = object()
    service._session_repository.session = expected

    result = await service.get_session(
        uuid4(),
        uuid4(),
    )

    assert result is expected


@pytest.mark.asyncio
async def test_list_sessions_delegates(service):
    user_id = uuid4()
    expected = [object()]

    service._session_repository.list_by_user = AsyncMock(
        return_value=expected,
    )

    result = await service.list_sessions(
        user_id,
        status='active',
        offset=20,
        limit=20,
    )

    assert result == expected


@pytest.mark.asyncio
async def test_count_sessions_delegates(service):
    user_id = uuid4()

    service._session_repository.count_by_user = AsyncMock(
        return_value=17,
    )

    result = await service.count_sessions(
        user_id,
        status='passed',
    )

    assert result == 17


@pytest.mark.asyncio
async def test_create_session(service):
    user_id = uuid4()
    repertoire_id = uuid4()
    root_id = uuid4()

    root = TrainingLine(
        id=root_id,
        parent_id=None,
        tag=None,
        moves=['e2e4'],
        analytic_version=2,
    )

    tree = TrainingTree(
        repertoire_revision=5,
        lines=[root],
    )

    client = FakeRepertoireClient(tree)

    service._repertoire_client = client
    service._stats_repository = FakeStatsRepository()
    service._selector = FakeSelector(
        SimpleNamespace(
            lines=[root],
            moves=['e2e4'],
        )
    )

    result = await service.create_session(
        user_id=user_id,
        data=TrainingSessionCreate(
            repertoire_id=repertoire_id,
            line_id=None,
        ),
    )

    assert result.status == TrainingSessionStatus.ACTIVE
    assert result.user_id == user_id
    assert result.repertoire_id == repertoire_id
    assert result.start_line_id == root_id
    assert result.current_ply == 0
    assert result.repertoire_revision == 5
    assert result.selected_moves == ['e2e4']

    assert result.selected_path == [
        {
            'line_id': str(root_id),
            'moves_count': 1,
            'analytic_version': 2,
        },
    ]

    assert service._session.commit_count == 1
    assert service._session.refresh_count == 1


@pytest.mark.asyncio
async def test_make_move_not_found(service):
    service._session_repository.session = None

    with pytest.raises(TrainingSessionNotFoundError):
        await service.make_move(
            uuid4(),
            uuid4(),
            'e2e4',
        )


@pytest.mark.asyncio
async def test_make_move_not_active(service):
    training_session = SimpleNamespace(
        status=TrainingSessionStatus.PASSED,
    )

    service._session_repository.session = training_session

    with pytest.raises(TrainingSessionNotActiveError):
        await service.make_move(
            uuid4(),
            uuid4(),
            'e2e4',
        )


@pytest.mark.asyncio
async def test_make_move_revision_mismatch(
    service,
    monkeypatch,
):
    user_id = uuid4()
    session_id = uuid4()

    training_session = SimpleNamespace(
        status=TrainingSessionStatus.ACTIVE,
        repertoire_id=uuid4(),
        repertoire_revision=1,
    )

    service._session_repository.session = training_session

    service._repertoire_client = FakeRepertoireClient(
        TrainingTree(
            repertoire_revision=1,
            lines=[],
        ),
        revision=2,
    )

    invalidated = False

    async def fake_invalidate(session_id, user_id):
        nonlocal invalidated
        invalidated = True

    monkeypatch.setattr(
        service,
        '_invalidate_session',
        fake_invalidate,
    )

    with pytest.raises(TrainingSessionInvalidatedError):
        await service.make_move(
            session_id,
            user_id,
            'e2e4',
        )

    assert invalidated is True
    assert service._session.rollback_count == 1


@pytest.mark.asyncio
async def test_find_line_for_ply(service):
    line1 = uuid4()
    line2 = uuid4()

    selected_path = [
        {
            'line_id': str(line1),
            'moves_count': 2,
            'analytic_version': 1,
        },
        {
            'line_id': str(line2),
            'moves_count': 3,
            'analytic_version': 4,
        },
    ]

    assert (
        service._find_line_for_ply(
            TrainingSession(
                selected_path=selected_path,
            ),
            0,
        )
        == line1
    )

    assert (
        service._find_line_for_ply(
            TrainingSession(
                selected_path=selected_path,
            ),
            2,
        )
        == line2
    )

    assert (
        service._find_line_for_ply(
            TrainingSession(
                selected_path=selected_path,
            ),
            4,
        )
        == line2
    )


def test_find_line_for_ply_out_of_range(service):
    selected_path = [
        {
            'line_id': str(uuid4()),
            'moves_count': 1,
            'analytic_version': 1,
        },
    ]

    training_session = TrainingSession(
        selected_path=selected_path,
    )

    with pytest.raises(RuntimeError):
        service._find_line_for_ply(
            training_session,
            1,
        )


def test_get_passed_line_ids(service):
    line1 = uuid4()
    line2 = uuid4()
    line3 = uuid4()

    selected_path = [
        {'line_id': str(line1)},
        {'line_id': str(line2)},
        {'line_id': str(line3)},
    ]

    training_session = TrainingSession(
        selected_path=selected_path,
    )

    assert service._get_passed_line_ids(
        training_session,
        line3,
    ) == [line1, line2]

    assert service._get_passed_line_ids(
        training_session,
        line1,
    ) == []


def test_get_line_version(service):
    line_id = uuid4()

    selected_path = [
        {
            'line_id': str(line_id),
            'analytic_version': 7,
        },
    ]

    training_session = TrainingSession(
        selected_path=selected_path,
    )

    assert (
        service._get_line_version(
            training_session,
            line_id,
        )
        == 7
    )


def test_get_line_version_missing(service):
    training_session = TrainingSession(
        selected_path=[],
    )

    with pytest.raises(RuntimeError):
        service._get_line_version(
            training_session,
            uuid4(),
        )
