from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from exceptions import (
    TrainingSessionInvalidatedError,
    TrainingSessionNotFoundError,
)
from models.session import (
    TrainingSession,
    TrainingSessionStatus,
)
from models.stat import LineTrainingStats
from schemas.session import TrainingSessionCreate
from services.training import TrainingService


@pytest.mark.asyncio
async def test_create_session_persists_data(
    session,
    user_id,
    repertoire_id,
    fake_repertoire_client,
):
    service = TrainingService(
        session=session,
        repertoire_client=fake_repertoire_client,
    )

    result = await service.create_session(
        user_id=user_id,
        data=TrainingSessionCreate(
            repertoire_id=repertoire_id,
            line_id=None,
        ),
    )

    assert result.id is not None
    assert result.user_id == user_id
    assert result.repertoire_id == repertoire_id
    assert result.status == TrainingSessionStatus.ACTIVE
    assert result.repertoire_revision == 1
    assert result.selected_moves == [
        'e2e4',
        'e7e5',
    ]

    stored = await session.get(
        TrainingSession,
        result.id,
    )

    assert stored is not None
    assert stored.selected_path == [
        {
            'line_id': str(
                fake_repertoire_client.tree.lines[0].id
            ),
            'moves_count': 1,
            'analytic_version': 1,
        },
        {
            'line_id': str(
                fake_repertoire_client.tree.lines[1].id
            ),
            'moves_count': 1,
            'analytic_version': 1,
        },
    ]


@pytest.mark.asyncio
async def test_make_move_wrong_move_creates_failure_stats(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
    fake_repertoire_client,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
    )

    session.add(training_session)
    await session.commit()
    await session.refresh(training_session)

    training_session_id = training_session.id

    service = TrainingService(
        session=session,
        repertoire_client=fake_repertoire_client,
    )

    result = await service.make_move(
        user_id,
        training_session_id,
        'd2d4',
    )

    assert result.correct is False
    assert result.current_ply == 0
    assert result.status == TrainingSessionStatus.FAILED

    await session.refresh(training_session)

    assert training_session.status == (
        TrainingSessionStatus.FAILED
    )
    assert training_session.error_line_id == root_line_id
    assert training_session.error_ply == 0
    assert training_session.error_line_analytic_version == 1
    assert training_session.ended_at is not None

    stat = await session.scalar(
        select(LineTrainingStats).where(
            LineTrainingStats.user_id == user_id,
            LineTrainingStats.line_id == root_line_id,
            LineTrainingStats.line_analytic_version == 1,
        )
    )

    assert stat is not None
    assert stat.attempts == 1
    assert stat.fails == 1
    assert stat.consecutive_failures == 1
    assert stat.consecutive_successes == 0


@pytest.mark.asyncio
async def test_make_move_correct_final_move_passes_session(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
    fake_repertoire_client,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
    )

    session.add(training_session)
    await session.commit()
    await session.refresh(training_session)

    training_session_id = training_session.id

    service = TrainingService(
        session=session,
        repertoire_client=fake_repertoire_client,
    )

    result = await service.make_move(
        user_id,
        training_session_id,
        'e2e4',
    )

    assert result.correct is True
    assert result.current_ply == 1
    assert result.status == TrainingSessionStatus.PASSED

    await session.refresh(training_session)

    assert training_session.current_ply == 1
    assert training_session.status == (
        TrainingSessionStatus.PASSED
    )
    assert training_session.ended_at is not None

    stat = await session.scalar(
        select(LineTrainingStats).where(
            LineTrainingStats.user_id == user_id,
            LineTrainingStats.line_id == root_line_id,
            LineTrainingStats.line_analytic_version == 1,
        )
    )

    assert stat is not None
    assert stat.attempts == 1
    assert stat.fails == 0
    assert stat.consecutive_successes == 1


@pytest.mark.asyncio
async def test_make_move_success_then_failure_records_previous_success(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    child_line_id,
    make_training_session,
    fake_repertoire_client,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4', 'e7e5'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
            {
                'line_id': str(child_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
    )

    session.add(training_session)
    await session.commit()
    await session.refresh(training_session)

    training_session_id = training_session.id

    service = TrainingService(
        session=session,
        repertoire_client=fake_repertoire_client,
    )

    first = await service.make_move(
        user_id,
        training_session_id,
        'e2e4',
    )

    assert first.correct is True
    assert first.current_ply == 1
    assert first.status == TrainingSessionStatus.ACTIVE

    second = await service.make_move(
        user_id,
        training_session_id,
        'c7c5',
    )

    assert second.correct is False
    assert second.current_ply == 1
    assert second.status == TrainingSessionStatus.FAILED

    root_stat = await session.scalar(
        select(LineTrainingStats).where(
            LineTrainingStats.user_id == user_id,
            LineTrainingStats.line_id == root_line_id,
        )
    )

    child_stat = await session.scalar(
        select(LineTrainingStats).where(
            LineTrainingStats.user_id == user_id,
            LineTrainingStats.line_id == child_line_id,
        )
    )

    assert root_stat is not None
    assert root_stat.attempts == 1
    assert root_stat.fails == 0

    assert child_stat is not None
    assert child_stat.attempts == 1
    assert child_stat.fails == 1


@pytest.mark.asyncio
async def test_make_move_invalidates_on_repertoire_revision_change(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
    fake_repertoire_client,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
        repertoire_revision=1,
    )

    session.add(training_session)
    await session.commit()
    await session.refresh(training_session)

    training_session_id = training_session.id

    fake_repertoire_client.revision = 2

    service = TrainingService(
        session=session,
        repertoire_client=fake_repertoire_client,
    )

    with pytest.raises(TrainingSessionInvalidatedError):
        await service.make_move(
            user_id,
            training_session_id,
            'e2e4',
        )

    await session.refresh(training_session)

    assert training_session.status == (
        TrainingSessionStatus.INVALIDATED
    )
    assert training_session.ended_at is not None


@pytest.mark.asyncio
async def test_get_session_rejects_other_user(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
    )

    session.add(training_session)
    await session.commit()
    await session.refresh(training_session)

    training_session_id = training_session.id

    service = TrainingService(
        session=session,
        repertoire_client=MagicMock(),
    )

    with pytest.raises(TrainingSessionNotFoundError):
        await service.get_session(
            training_session_id,
            uuid4(),
        )
