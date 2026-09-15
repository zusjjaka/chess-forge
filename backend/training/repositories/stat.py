from uuid import UUID

from sqlalchemy import (
    select,
    tuple_,
)
from sqlalchemy.ext.asyncio import AsyncSession

from models.stat import LineTrainingStats


class LineTrainingStatsRepository:
    def __init__(self,
                 session: AsyncSession
                 ) -> None:
        self._session = session

    async def get(self,
                  line_id: UUID,
                  line_analytic_version: int,
                  *,
                  for_update: bool = False
                  ) -> LineTrainingStats | None:
        statement = select(LineTrainingStats).where(
            LineTrainingStats.line_id == line_id,
            LineTrainingStats.line_analytic_version == line_analytic_version,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_many(self,
                       line_keys: list[tuple[UUID, int]]
                       ) -> list[LineTrainingStats]:
        if not line_keys:
            return []

        statement = select(LineTrainingStats).where(
            tuple_(
                LineTrainingStats.line_id,
                LineTrainingStats.line_analytic_version,
            ).in_(line_keys),
        )

        result = await self._session.execute(statement)

        return list(result.scalars().all())

    async def add(self,
                  stats: LineTrainingStats
                  ) -> None:
        self._session.add(stats)
