import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.repertoire import (
    Repertoire,
    RepertoireSide,
)
from repositories.repertoire import RepertoireRepository


@pytest.mark.asyncio
async def test_create_and_get_by_id(
        session: AsyncSession,
        ) -> None:
    user_id = uuid.uuid4()

    repertoire = Repertoire(
        user_id=user_id,
        name='Italian Game',
        description='Test repertoire',
        side=RepertoireSide.WHITE,
    )

    repository = RepertoireRepository(session)

    created = await repository.create(repertoire)
    await session.commit()

    result = await repository.get_by_id(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.user_id == user_id
    assert result.name == 'Italian Game'


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing_repertoire(
        session: AsyncSession,
        ) -> None:
    repository = RepertoireRepository(session)

    result = await repository.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_for_user_returns_repertoire(
        session: AsyncSession,
        ) -> None:
    user_id = uuid.uuid4()

    repertoire = Repertoire(
        user_id=user_id,
        name='Sicilian Defense',
        description='',
        side=RepertoireSide.BLACK,
    )

    repository = RepertoireRepository(session)

    await repository.create(repertoire)
    await session.commit()

    result = await repository.get_by_id_for_user(
        repertoire.id,
        user_id,
    )

    assert result is not None
    assert result.id == repertoire.id


@pytest.mark.asyncio
async def test_get_by_id_for_user_returns_none_for_other_user(
        session: AsyncSession,
        ) -> None:
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    repertoire = Repertoire(
        user_id=owner_id,
        name='French Defense',
        description='',
        side=RepertoireSide.BLACK,
    )

    repository = RepertoireRepository(session)

    await repository.create(repertoire)
    await session.commit()

    result = await repository.get_by_id_for_user(
        repertoire.id,
        other_user_id,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_page_for_user_returns_only_users_repertoires(
        session: AsyncSession,
        ) -> None:
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()

    repository = RepertoireRepository(session)

    first = Repertoire(
        user_id=user_id,
        name='First',
        description='',
        side=RepertoireSide.WHITE,
    )
    second = Repertoire(
        user_id=user_id,
        name='Second',
        description='',
        side=RepertoireSide.BLACK,
    )
    other = Repertoire(
        user_id=other_user_id,
        name='Other',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repository.create(first)
    await repository.create(second)
    await repository.create(other)
    await session.commit()

    items, total = await repository.get_page_for_user(
        user_id,
        offset=0,
        limit=20,
    )

    assert total == 2
    assert len(items) == 2
    assert {item.id for item in items} == {
        first.id,
        second.id,
    }


@pytest.mark.asyncio
async def test_get_page_for_user_applies_offset_and_limit(
        session: AsyncSession,
        ) -> None:
    user_id = uuid.uuid4()

    repository = RepertoireRepository(session)

    repertoires = [
        Repertoire(
            user_id=user_id,
            name=f'Repertoire {index}',
            description='',
            side=RepertoireSide.WHITE,
        )
        for index in range(3)
    ]

    for repertoire in repertoires:
        await repository.create(repertoire)

    await session.commit()

    items, total = await repository.get_page_for_user(
        user_id,
        offset=1,
        limit=1,
    )

    assert total == 3
    assert len(items) == 1
    assert items[0].id == repertoires[1].id


@pytest.mark.asyncio
async def test_get_page_for_user_returns_empty_for_user_without_repertoires(
        session: AsyncSession,
        ) -> None:
    repository = RepertoireRepository(session)

    items, total = await repository.get_page_for_user(
        uuid.uuid4(),
        offset=0,
        limit=20,
    )

    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_update_version_succeeds_for_expected_version(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repository = RepertoireRepository(session)

    await repository.create(repertoire)
    await session.commit()

    result = await repository.update_version(
        repertoire.id,
        expected_version=1,
    )

    await session.commit()
    await session.refresh(repertoire)

    assert result is True
    assert repertoire.version == 2


@pytest.mark.asyncio
async def test_update_version_fails_for_stale_version(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repository = RepertoireRepository(session)

    await repository.create(repertoire)
    await session.commit()

    result = await repository.update_version(
        repertoire.id,
        expected_version=999,
    )

    await session.commit()
    await session.refresh(repertoire)

    assert result is False
    assert repertoire.version == 1


@pytest.mark.asyncio
async def test_delete_removes_repertoire(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repository = RepertoireRepository(session)

    await repository.create(repertoire)
    await session.commit()

    await repository.delete(repertoire)
    await session.commit()

    result = await repository.get_by_id(repertoire.id)

    assert result is None
