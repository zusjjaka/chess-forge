from datetime import (
    datetime,
    timedelta,
)
from uuid import (
    UUID,
    uuid4,
)

from sqlalchemy.ext.asyncio import AsyncSession

from models.stat import LineTrainingStats
from repositories.stat import LineTrainingStatsRepository


async def test_add_and_get(
        session: AsyncSession,
        ) -> None:
    repository = LineTrainingStatsRepository(session)

    line_id = uuid4()

    stats = LineTrainingStats(
        line_id=line_id,
        line_analytic_version=1,
    )

    await repository.add(stats)
    await session.flush()

    result = await repository.get(
        line_id,
        1,
    )

    assert result is stats
    assert result.attempts == 0
    assert result.fails == 0
    assert result.consecutive_successes == 0
    assert result.consecutive_failures == 0
    assert result.target_interval == timedelta(days=1)


async def test_get_returns_none_for_missing_stats(
        session: AsyncSession,
        ) -> None:
    repository = LineTrainingStatsRepository(session)

    result = await repository.get(
        uuid4(),
        1,
    )

    assert result is None


async def test_get_distinguishes_line_versions(
        session: AsyncSession,
        ) -> None:
    repository = LineTrainingStatsRepository(session)

    line_id = uuid4()

    version_one = LineTrainingStats(
        line_id=line_id,
        line_analytic_version=1,
        attempts=10,
        fails=3,
    )

    version_two = LineTrainingStats(
        line_id=line_id,
        line_analytic_version=2,
        attempts=2,
        fails=1,
    )

    await repository.add(version_one)
    await repository.add(version_two)
    await session.flush()

    result_v1 = await repository.get(line_id, 1)
    result_v2 = await repository.get(line_id, 2)

    assert result_v1 is version_one
    assert result_v2 is version_two


async def test_get_for_update(
        session: AsyncSession,
        ) -> None:
    repository = LineTrainingStatsRepository(session)

    stats = LineTrainingStats(
        line_id=uuid4(),
        line_analytic_version=1,
        attempts=5,
        fails=2,
    )

    await repository.add(stats)
    await session.flush()

    result = await repository.get(
        stats.line_id,
        stats.line_analytic_version,
        for_update=True,
    )

    assert result is stats


async def test_get_many(
        session: AsyncSession,
        ) -> None:
    repository = LineTrainingStatsRepository(session)

    line_id_one = uuid4()
    line_id_two = uuid4()
    line_id_three = uuid4()

    stats_one = LineTrainingStats(
        line_id=line_id_one,
        line_analytic_version=1,
        attempts=5,
        fails=2,
    )

    stats_two = LineTrainingStats(
        line_id=line_id_two,
        line_analytic_version=3,
        attempts=10,
        fails=1,
    )

    stats_three = LineTrainingStats(
        line_id=line_id_three,
        line_analytic_version=1,
        attempts=3,
        fails=3,
    )

    await repository.add(stats_one)
    await repository.add(stats_two)
    await repository.add(stats_three)
    await session.flush()

    result = await repository.get_many(
        [
            (line_id_one, 1),
            (line_id_two, 3),
        ],
    )

    assert len(result) == 2
    assert {item.line_id for item in result} == {
        line_id_one,
        line_id_two,
    }


async def test_get_many_returns_empty_list_for_empty_input(
        session: AsyncSession,
        ) -> None:
    repository = LineTrainingStatsRepository(session)

    result = await repository.get_many([])

    assert result == []
