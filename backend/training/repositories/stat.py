from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.stat import LineTrainingStats


class LineTrainingStatsRepository:
    def __init__(
            self,
            session: AsyncSession,
            ) -> None:
        self._session = session

    async def add(
            self,
            stats: LineTrainingStats,
            ) -> None:
        self._session.add(stats)

    async def get(
            self,
            user_id: UUID,
            line_id: UUID,
            line_analytic_version: int,
            *,
            for_update: bool = False,
            ) -> LineTrainingStats | None:

        statement = select(LineTrainingStats).where(
            LineTrainingStats.user_id == user_id,
            LineTrainingStats.line_id == line_id,
            LineTrainingStats.line_analytic_version
            == line_analytic_version,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_many(
            self,
            user_id: UUID,
            line_keys: list[tuple[UUID, int]],
            ) -> list[LineTrainingStats]:

        if not line_keys:
            return []

        conditions = [
            (
                LineTrainingStats.line_id == line_id
            ) & (
                LineTrainingStats.line_analytic_version == version
            )
            for line_id, version in line_keys
        ]

        result = await self._session.execute(
            select(LineTrainingStats).where(
                LineTrainingStats.user_id == user_id,
                or_(*conditions),
            ),
        )

        return list(result.scalars())

    async def increment_success(
            self,
            user_id: UUID,
            line_id: UUID,
            line_analytic_version: int,
            ) -> None:

        now = datetime.now(UTC)

        statement = insert(LineTrainingStats).values(
            user_id=user_id,
            line_id=line_id,
            line_analytic_version=line_analytic_version,
            attempts=1,
            fails=0,
            consecutive_successes=1,
            consecutive_failures=0,
            last_attempt_at=now,
        )

        statement = statement.on_conflict_do_update(
            constraint='uq_line_training_stats_user_line_version',
            set_={
                'attempts': LineTrainingStats.attempts + 1,
                'consecutive_successes': (
                    LineTrainingStats.consecutive_successes + 1
                ),
                'consecutive_failures': 0,
                'last_attempt_at': now,
                'updated_at': now,
            },
        )

        await self._session.execute(statement)

    async def increment_failure(
            self,
            user_id: UUID,
            line_id: UUID,
            line_analytic_version: int,
            ) -> None:

        now = datetime.now(UTC)

        statement = insert(LineTrainingStats).values(
            user_id=user_id,
            line_id=line_id,
            line_analytic_version=line_analytic_version,
            attempts=1,
            fails=1,
            consecutive_successes=0,
            consecutive_failures=1,
            last_attempt_at=now,
        )

        statement = statement.on_conflict_do_update(
            constraint='uq_line_training_stats_user_line_version',
            set_={
                'attempts': LineTrainingStats.attempts + 1,
                'fails': LineTrainingStats.fails + 1,
                'consecutive_successes': 0,
                'consecutive_failures': (
                    LineTrainingStats.consecutive_failures + 1
                ),
                'last_attempt_at': now,
                'updated_at': now,
            },
        )

        await self._session.execute(statement)
