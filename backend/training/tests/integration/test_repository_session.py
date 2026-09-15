from uuid import (
    UUID,
    uuid4,
)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.session import (
    TrainingSession,
    TrainingSessionStatus,
)
from repositories.session import (
    TrainingSessionRepository,
)


@pytest.fixture
def repository(
        session: AsyncSession,
        ) -> TrainingSessionRepository:
    return TrainingSessionRepository(session)


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def repertoire_id() -> UUID:
    return uuid4()


@pytest.fixture
def start_line_id() -> UUID:
    return uuid4()


@pytest.fixture
def training_session(
        user_id: UUID,
        repertoire_id: UUID,
        start_line_id: UUID,
        ) -> TrainingSession:
    return TrainingSession(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=start_line_id,
        repertoire_revision=1,
        selected_moves=[
            'e2e4',
            'e7e5',
            'g1f3',
        ],
        selected_path=[
            {
                'line_id': str(start_line_id),
                'start_ply': 0,
                'end_ply': 3,
            },
        ],
        status=TrainingSessionStatus.ACTIVE,
    )


async def test_add_and_get(
        repository: TrainingSessionRepository,
        session: AsyncSession,
        training_session: TrainingSession,
        ) -> None:
    await repository.add(training_session)
    await session.flush()

    result = await repository.get(training_session.id)

    assert result is training_session


async def test_get_returns_none_for_missing_session(
        repository: TrainingSessionRepository,
        ) -> None:
    result = await repository.get(uuid4())

    assert result is None


async def test_get_for_update(
        repository: TrainingSessionRepository,
        session: AsyncSession,
        training_session: TrainingSession,
        ) -> None:
    await repository.add(training_session)
    await session.flush()

    result = await repository.get(
        training_session.id,
        for_update=True,
    )

    assert result is training_session


async def test_list_by_user(
        repository: TrainingSessionRepository,
        session: AsyncSession,
        user_id: UUID,
        repertoire_id: UUID,
        start_line_id: UUID,
        ) -> None:
    first_session = TrainingSession(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=start_line_id,
        repertoire_revision=1,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(start_line_id),
                'start_ply': 0,
                'end_ply': 1,
            },
        ],
        status=TrainingSessionStatus.ACTIVE,
    )

    second_session = TrainingSession(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=start_line_id,
        repertoire_revision=1,
        selected_moves=['e2e4', 'e7e5'],
        selected_path=[
            {
                'line_id': str(start_line_id),
                'start_ply': 0,
                'end_ply': 2,
            },
        ],
        status=TrainingSessionStatus.PASSED,
    )

    await repository.add(first_session)
    await repository.add(second_session)
    await session.flush()

    result = await repository.list_by_user(user_id)

    assert len(result) == 2
    assert {item.id for item in result} == {
        first_session.id,
        second_session.id,
    }


async def test_list_by_user_filters_by_status(
        repository: TrainingSessionRepository,
        session: AsyncSession,
        user_id: UUID,
        repertoire_id: UUID,
        start_line_id: UUID,
        ) -> None:
    active_session = TrainingSession(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=start_line_id,
        repertoire_revision=1,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(start_line_id),
                'start_ply': 0,
                'end_ply': 1,
            },
        ],
        status=TrainingSessionStatus.ACTIVE,
    )

    passed_session = TrainingSession(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=start_line_id,
        repertoire_revision=1,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(start_line_id),
                'start_ply': 0,
                'end_ply': 1,
            },
        ],
        status=TrainingSessionStatus.PASSED,
    )

    await repository.add(active_session)
    await repository.add(passed_session)
    await session.flush()

    result = await repository.list_by_user(
        user_id,
        status=TrainingSessionStatus.ACTIVE,
    )

    assert len(result) == 1
    assert result[0].id == active_session.id


async def test_list_by_user_does_not_return_other_user_sessions(
        repository: TrainingSessionRepository,
        session: AsyncSession,
        user_id: UUID,
        repertoire_id: UUID,
        start_line_id: UUID,
        ) -> None:
    own_session = TrainingSession(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=start_line_id,
        repertoire_revision=1,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.ACTIVE,
    )

    other_user_session = TrainingSession(
        user_id=uuid4(),
        repertoire_id=repertoire_id,
        start_line_id=start_line_id,
        repertoire_revision=1,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.ACTIVE,
    )

    await repository.add(own_session)
    await repository.add(other_user_session)
    await session.flush()

    result = await repository.list_by_user(user_id)

    assert len(result) == 1
    assert result[0].id == own_session.id
