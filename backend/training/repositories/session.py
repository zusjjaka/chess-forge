from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import PAGE_SIZE
from models.session import (
    TrainingSession,
    TrainingSessionStatus,
)


class TrainingSessionRepository:
    def __init__(
            self,
            session: AsyncSession,
            ) -> None:
        self._session = session

    async def get(
            self,
            session_id: UUID,
            user_id: UUID,
            *,
            for_update: bool = False,
            ) -> TrainingSession | None:

        statement = select(TrainingSession).where(
            TrainingSession.id == session_id,
            TrainingSession.user_id == user_id,
        )

        if for_update:
            statement = statement.with_for_update()

        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def add(
            self,
            training_session: TrainingSession,
            ) -> None:
        self._session.add(training_session)

    async def list_by_user(
            self,
            user_id: UUID,
            *,
            status: TrainingSessionStatus | None = None,
            offset: int = 0,
            limit: int = PAGE_SIZE,
            ) -> list[TrainingSession]:

        statement = (
            select(TrainingSession)
            .where(
                TrainingSession.user_id == user_id,
            )
            .order_by(
                TrainingSession.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )

        if status is not None:
            statement = statement.where(
                TrainingSession.status == status,
            )

        result = await self._session.execute(statement)

        return list(result.scalars())

    async def count_by_user(
            self,
            user_id: UUID,
            *,
            status: TrainingSessionStatus | None = None,
            ) -> int:

        statement = select(
            func.count(),
        ).select_from(
            TrainingSession,
        ).where(
            TrainingSession.user_id == user_id,
        )

        if status is not None:
            statement = statement.where(
                TrainingSession.status == status,
            )

        result = await self._session.execute(statement)

        return result.scalar_one()
