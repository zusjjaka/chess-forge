from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.session import (
    TrainingSession,
    TrainingSessionStatus,
)
from models.stat import LineTrainingStats
from repositories.session import TrainingSessionRepository
from repositories.stat import LineTrainingStatsRepository


@pytest.mark.asyncio
async def test_session_repository_get(
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

    repository = TrainingSessionRepository(session)

    result = await repository.get(
        training_session.id,
        user_id,
    )

    assert result is not None
    assert result.id == training_session.id


@pytest.mark.asyncio
async def test_session_repository_get_does_not_return_other_user(
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

    repository = TrainingSessionRepository(session)

    result = await repository.get(
        training_session.id,
        uuid4(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_session_repository_list_and_count(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    now = datetime.now(timezone.utc)

    sessions = []

    for index in range(3):
        item = make_training_session(
            user_id=user_id,
            repertoire_id=repertoire_id,
            start_line_id=root_line_id,
            selected_moves=['e2e4'],
            selected_path=[],
        )
        item.created_at = now + timedelta(minutes=index)
        item.status = (
            TrainingSessionStatus.PASSED
            if index == 0
            else TrainingSessionStatus.ACTIVE
        )
        sessions.append(item)

    session.add_all(sessions)
    await session.commit()

    repository = TrainingSessionRepository(session)

    result = await repository.list_by_user(
        user_id,
    )

    assert [item.id for item in result] == [
        sessions[2].id,
        sessions[1].id,
        sessions[0].id,
    ]

    assert (
        await repository.count_by_user(user_id)
        == 3
    )


@pytest.mark.asyncio
async def test_session_repository_filters_by_status(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    active = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.ACTIVE,
    )

    passed = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.PASSED,
    )

    session.add_all([active, passed])
    await session.commit()

    repository = TrainingSessionRepository(session)

    result = await repository.list_by_user(
        user_id,
        status=TrainingSessionStatus.PASSED,
    )

    assert [item.id for item in result] == [passed.id]

    assert (
        await repository.count_by_user(
            user_id,
            status=TrainingSessionStatus.PASSED,
        )
        == 1
    )


@pytest.mark.asyncio
async def test_session_repository_pagination(
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    now = datetime.now(timezone.utc)

    sessions = []

    for index in range(5):
        item = make_training_session(
            user_id=user_id,
            repertoire_id=repertoire_id,
            start_line_id=root_line_id,
            selected_moves=['e2e4'],
            selected_path=[],
        )
        item.created_at = now + timedelta(minutes=index)
        sessions.append(item)

    session.add_all(sessions)
    await session.commit()

    repository = TrainingSessionRepository(session)

    result = await repository.list_by_user(
        user_id,
        offset=1,
        limit=2,
    )

    assert [item.id for item in result] == [
        sessions[3].id,
        sessions[2].id,
    ]


@pytest.mark.asyncio
async def test_stat_repository_get_many(
    session,
    user_id,
):
    line1 = uuid4()
    line2 = uuid4()

    stat1 = LineTrainingStats(
        user_id=user_id,
        line_id=line1,
        line_analytic_version=1,
    )

    stat2 = LineTrainingStats(
        user_id=user_id,
        line_id=line2,
        line_analytic_version=2,
    )

    session.add_all([stat1, stat2])
    await session.commit()

    repository = LineTrainingStatsRepository(session)

    result = await repository.get_many(
        user_id,
        [
            (line1, 1),
            (line2, 2),
        ],
    )

    assert {
        (item.line_id, item.line_analytic_version)
        for item in result
    } == {
        (line1, 1),
        (line2, 2),
    }


@pytest.mark.asyncio
async def test_stat_repository_get_many_empty(
    session,
    user_id,
):
    repository = LineTrainingStatsRepository(session)

    assert (
        await repository.get_many(user_id, [])
        == []
    )


@pytest.mark.asyncio
async def test_increment_success(
    session,
    user_id,
):
    line_id = uuid4()

    repository = LineTrainingStatsRepository(session)

    await repository.increment_success(
        user_id,
        line_id,
        1,
    )
    await session.commit()

    result = await repository.get(
        user_id,
        line_id,
        1,
    )

    assert result is not None
    assert result.attempts == 1
    assert result.fails == 0
    assert result.consecutive_successes == 1
    assert result.consecutive_failures == 0


@pytest.mark.asyncio
async def test_increment_failure(
    session,
    user_id,
):
    line_id = uuid4()

    repository = LineTrainingStatsRepository(session)

    await repository.increment_failure(
        user_id,
        line_id,
        1,
    )
    await session.commit()

    result = await repository.get(
        user_id,
        line_id,
        1,
    )

    assert result is not None
    assert result.attempts == 1
    assert result.fails == 1
    assert result.consecutive_successes == 0
    assert result.consecutive_failures == 1


@pytest.mark.asyncio
async def test_stat_streaks_reset(
    session,
    user_id,
):
    line_id = uuid4()

    repository = LineTrainingStatsRepository(session)

    await repository.increment_success(
        user_id,
        line_id,
        1,
    )
    await repository.increment_success(
        user_id,
        line_id,
        1,
    )
    await session.commit()
    session.expire_all()

    result = await repository.get(
        user_id,
        line_id,
        1,
    )

    assert result is not None
    assert result.attempts == 2
    assert result.consecutive_successes == 2

    await repository.increment_failure(
        user_id,
        line_id,
        1,
    )
    await session.commit()
    session.expire_all()

    result = await repository.get(
        user_id,
        line_id,
        1,
    )

    assert result is not None
    assert result.attempts == 3
    assert result.fails == 1
    assert result.consecutive_successes == 0
    assert result.consecutive_failures == 1

    await repository.increment_success(
        user_id,
        line_id,
        1,
    )
    await session.commit()
    session.expire_all()

    result = await repository.get(
        user_id,
        line_id,
        1,
    )

    assert result is not None
    assert result.attempts == 4
    assert result.fails == 1
    assert result.consecutive_successes == 1
    assert result.consecutive_failures == 0


@pytest.mark.asyncio
async def test_stat_unique_constraint(
    session,
    user_id,
):
    line_id = uuid4()

    session.add_all(
        [
            LineTrainingStats(
                user_id=user_id,
                line_id=line_id,
                line_analytic_version=1,
            ),
            LineTrainingStats(
                user_id=user_id,
                line_id=line_id,
                line_analytic_version=1,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_stat_rejects_version_zero(
    session,
    user_id,
):
    session.add(
        LineTrainingStats(
            user_id=user_id,
            line_id=uuid4(),
            line_analytic_version=0,
        )
    )

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_stat_rejects_fails_greater_than_attempts(
    session,
    user_id,
):
    session.add(
        LineTrainingStats(
            user_id=user_id,
            line_id=uuid4(),
            line_analytic_version=1,
            attempts=1,
            fails=2,
        )
    )

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_stat_rejects_non_positive_interval(
    session,
    user_id,
):
    session.add(
        LineTrainingStats(
            user_id=user_id,
            line_id=uuid4(),
            line_analytic_version=1,
            target_interval=0,
        )
    )

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_session_rejects_negative_current_ply(
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
        current_ply=-1,
    )

    session.add(training_session)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()


@pytest.mark.asyncio
async def test_session_rejects_negative_revision(
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
        repertoire_revision=-1,
    )

    session.add(training_session)

    with pytest.raises(IntegrityError):
        await session.commit()

    await session.rollback()
