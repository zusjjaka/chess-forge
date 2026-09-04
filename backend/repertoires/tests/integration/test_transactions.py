import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.repertoire import (
    Line,
    Repertoire,
    RepertoireSide,
)
from repositories.line import LineRepository
from repositories.repertoire import RepertoireRepository


@pytest.mark.asyncio
async def test_repertoire_creation_is_committed(
        session: AsyncSession,
        ) -> None:
    repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Italian Game',
        description='Test',
        side=RepertoireSide.WHITE,
    )

    await repository.create(repertoire)

    repertoire_id = repertoire.id

    await session.commit()

    result = await session.execute(
        select(Repertoire).where(
            Repertoire.id == repertoire_id,
        )
    )

    saved = result.scalar_one_or_none()

    assert saved is not None
    assert saved.id == repertoire_id


@pytest.mark.asyncio
async def test_repertoire_creation_is_rolled_back(
        session: AsyncSession,
        ) -> None:
    repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Italian Game',
        description='Test',
        side=RepertoireSide.WHITE,
    )

    await repository.create(repertoire)

    repertoire_id = repertoire.id

    await session.rollback()

    result = await session.execute(
        select(Repertoire).where(
            Repertoire.id == repertoire_id,
        )
    )

    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_line_creation_is_rolled_back_with_parent_transaction(
        session: AsyncSession,
        ) -> None:
    repertoire_repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Italian Game',
        description='Test',
        side=RepertoireSide.WHITE,
    )

    await repertoire_repository.create(repertoire)

    repertoire_id = repertoire.id

    line = Line(
        repertoire_id=repertoire_id,
        parent_id=None,
        moves=['e2e4'],
    )

    session.add(line)

    line_id = line.id

    await session.rollback()

    repertoire_result = await session.execute(
        select(Repertoire).where(
            Repertoire.id == repertoire_id,
        )
    )
    line_result = await session.execute(
        select(Line).where(
            Line.id == line_id,
        )
    )

    assert repertoire_result.scalar_one_or_none() is None
    assert line_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_version_increment_is_persisted(
        session: AsyncSession,
        ) -> None:
    repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repository.create(repertoire)
    await session.commit()

    repertoire.version += 1

    await session.commit()

    await session.refresh(repertoire)

    assert repertoire.version == 2


@pytest.mark.asyncio
async def test_stale_version_update_does_not_modify_version(
        session: AsyncSession,
        ) -> None:
    repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repository.create(repertoire)
    await session.commit()

    result = await repository.update_version(
        repertoire.id,
        expected_version=1,
    )

    assert result is True

    await session.commit()
    await session.refresh(repertoire)

    assert repertoire.version == 2

    stale_result = await repository.update_version(
        repertoire.id,
        expected_version=1,
    )

    assert stale_result is False

    await session.commit()
    await session.refresh(repertoire)

    assert repertoire.version == 2


@pytest.mark.asyncio
async def test_two_sequential_version_updates_require_current_version(
        session: AsyncSession,
        ) -> None:
    repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repository.create(repertoire)
    await session.commit()

    first_update = await repository.update_version(
        repertoire.id,
        expected_version=1,
    )

    await session.commit()

    second_update = await repository.update_version(
        repertoire.id,
        expected_version=2,
    )

    await session.commit()
    await session.refresh(repertoire)

    assert first_update is True
    assert second_update is True
    assert repertoire.version == 3


@pytest.mark.asyncio
async def test_transaction_rolls_back_on_integrity_error(
        session: AsyncSession,
        ) -> None:
    repertoire_repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repertoire_repository.create(repertoire)

    repertoire_id = repertoire.id

    first_root = Line(
        repertoire_id=repertoire_id,
        parent_id=None,
        moves=['e2e4'],
    )

    second_root = Line(
        repertoire_id=repertoire_id,
        parent_id=None,
        moves=['d2d4'],
    )

    session.add(first_root)
    await session.flush()

    session.add(second_root)

    with pytest.raises(Exception):
        await session.flush()

    await session.rollback()

    result = await session.execute(
        select(Line).where(
            Line.repertoire_id == repertoire_id,
        )
    )

    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_delete_transaction_is_committed(
        session: AsyncSession,
        ) -> None:
    repertoire_repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repertoire_repository.create(repertoire)

    repertoire_id = repertoire.id

    await session.commit()

    await repertoire_repository.delete(repertoire)
    await session.commit()

    result = await session.execute(
        select(Repertoire).where(
            Repertoire.id == repertoire_id,
        )
    )

    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_transaction_is_rolled_back(
        session: AsyncSession,
        ) -> None:
    repertoire_repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repertoire_repository.create(repertoire)

    repertoire_id = repertoire.id

    await session.commit()

    await repertoire_repository.delete(repertoire)
    await session.rollback()

    result = await session.execute(
        select(Repertoire).where(
            Repertoire.id == repertoire_id,
        )
    )

    assert result.scalar_one_or_none() is not None
