import uuid

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from models.repertoire import Repertoire


class RepertoireRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, repertoire: Repertoire) -> Repertoire:
        self.session.add(repertoire)
        await self.session.flush()

        return repertoire

    async def get_by_id(
            self,
            repertoire_id: uuid.UUID,
            ) -> Repertoire | None:
        result = await self.session.execute(
            select(Repertoire).where(
                Repertoire.id == repertoire_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_id_for_user(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> Repertoire | None:
        result = await self.session.execute(
            select(Repertoire).where(
                Repertoire.id == repertoire_id,
                Repertoire.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_id_for_user_for_update(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> Repertoire | None:
        result = await self.session.execute(
            select(Repertoire)
            .where(
                Repertoire.id == repertoire_id,
                Repertoire.user_id == user_id,
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def get_page_for_user(
            self,
            user_id: uuid.UUID,
            offset: int,
            limit: int,
            ) -> tuple[list[Repertoire], int]:
        items_result = await self.session.execute(
            select(Repertoire)
            .where(Repertoire.user_id == user_id)
            .order_by(Repertoire.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        count_result = await self.session.execute(
            select(func.count())
            .select_from(Repertoire)
            .where(Repertoire.user_id == user_id)
        )

        return (
            list(items_result.scalars().all()),
            count_result.scalar_one(),
        )

    async def delete(self, repertoire: Repertoire) -> None:
        await self.session.delete(repertoire)
