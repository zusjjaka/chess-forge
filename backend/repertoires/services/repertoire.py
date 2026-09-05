import uuid
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import RepertoireNotFoundError
from models.repertoire import Repertoire
from repositories.repertoire import RepertoireRepository
from schemas.repertoire import (
    RepertoireCreate,
    RepertoireUpdate,
)

PAGE_SIZE = 20


class RepertoireService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repertoire_repository = RepertoireRepository(
            session=session,
        )

    async def create(
            self,
            user_id: uuid.UUID,
            data: RepertoireCreate,
            ) -> Repertoire:
        async with self.session.begin():
            repertoire = Repertoire(
                user_id=user_id,
                name=data.name,
                description=data.description,
                side=data.side,
                version=1,
            )

            await self.repertoire_repository.create(
                repertoire,
            )

        return repertoire

    async def get(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> Repertoire:
        repertoire = await self.repertoire_repository.get_by_id_for_user(
            repertoire_id,
            user_id,
        )

        if repertoire is None:
            raise RepertoireNotFoundError

        return repertoire

    async def list(
            self,
            user_id: uuid.UUID,
            page: int,
            ) -> tuple[list[Repertoire], int, int]:
        offset = (page - 1) * PAGE_SIZE

        items, total = await self.repertoire_repository.get_page_for_user(
            user_id,
            offset,
            PAGE_SIZE,
        )

        pages = ceil(total / PAGE_SIZE) if total else 1

        return items, page, pages

    async def update(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            data: RepertoireUpdate,
            ) -> Repertoire:
        async with self.session.begin():
            repertoire = await self.get(
                repertoire_id,
                user_id,
            )

            fields = data.model_dump(exclude_unset=True)

            if 'name' in fields:
                repertoire.name = str(fields.get('name'))

            if 'description' in fields:
                repertoire.description = str(fields.get('description') or '')

        await self.session.refresh(repertoire)

        return repertoire

    async def delete(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> None:
        async with self.session.begin():
            repertoire = await self.repertoire_repository.get_by_id_for_user_for_update(
                repertoire_id,
                user_id,
            )

            if repertoire is None:
                raise RepertoireNotFoundError

            await self.repertoire_repository.delete(repertoire)
