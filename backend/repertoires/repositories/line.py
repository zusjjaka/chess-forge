import uuid

from sqlalchemy import (
    exists,
    literal,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from models.repertoire import Line


class LineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, line: Line) -> Line:
        self.session.add(line)
        await self.session.flush()

        return line

    async def get_by_id(
            self,
            line_id: uuid.UUID
            ) -> Line | None:
        result = await self.session.execute(
            select(Line).where(
                Line.id == line_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_id_and_repertoire(
            self,
            line_id: uuid.UUID,
            repertoire_id: uuid.UUID,
            ) -> Line | None:
        result = await self.session.execute(
            select(Line).where(
                Line.id == line_id,
                Line.repertoire_id == repertoire_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_root(
            self,
            repertoire_id: uuid.UUID,
            ) -> Line | None:
        result = await self.session.execute(
            select(Line).where(
                Line.repertoire_id == repertoire_id,
                Line.parent_id.is_(None),
            )
        )

        return result.scalar_one_or_none()

    async def get_all_by_repertoire(
            self,
            repertoire_id: uuid.UUID,
            ) -> list[Line]:
        result = await self.session.execute(
            select(Line)
            .where(Line.repertoire_id == repertoire_id)
            .order_by(Line.created_at)
        )

        return list(result.scalars().all())

    async def get_path_to_root(
            self,
            line_id: uuid.UUID,
            repertoire_id: uuid.UUID,
            ) -> list[Line]:
        path = (
            select(
                Line.id.label('id'),
                Line.parent_id.label('parent_id'),
                literal(0).label('depth'),
            )
            .where(
                Line.id == line_id,
                Line.repertoire_id == repertoire_id,
            )
            .cte(
                name='line_path',
                recursive=True,
            )
        )

        parent = Line.__table__.alias('parent')

        path = path.union_all(
            select(
                parent.c.id,
                parent.c.parent_id,
                (path.c.depth + 1).label('depth'),
            )
            .where(
                parent.c.id == path.c.parent_id,
                parent.c.repertoire_id == repertoire_id,
            )
        )

        result = await self.session.execute(
            select(Line)
            .join(
                path,
                Line.id == path.c.id,
            )
            .order_by(
                path.c.depth.desc(),
            )
        )

        return list(result.scalars().all())

    async def has_children(
            self,
            line_id: uuid.UUID,
            ) -> bool:
        result = await self.session.execute(
            select(
                exists().where(
                    Line.parent_id == line_id,
                )
            )
        )

        return result.scalar_one()

    async def delete(self, line: Line) -> None:
        await self.session.delete(line)
