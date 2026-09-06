import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.line import Line
from models.repertoire import (
    Repertoire,
    RepertoireSide,
)
from repositories.line import LineRepository
from repositories.repertoire import RepertoireRepository


@pytest.mark.asyncio
async def test_only_one_root_per_repertoire(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repertoire_repository = RepertoireRepository(session)

    await repertoire_repository.create(repertoire)

    first_root = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['e2e4'],
    )

    second_root = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['d2d4'],
    )

    session.add(first_root)
    await session.flush()

    session.add(second_root)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_child_must_reference_parent_from_same_repertoire(
        session: AsyncSession,
        ) -> None:
    repertoire_repository = RepertoireRepository(session)
    line_repository = LineRepository(session)

    first_repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='First',
        description='',
        side=RepertoireSide.WHITE,
    )
    second_repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Second',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repertoire_repository.create(first_repertoire)
    await repertoire_repository.create(second_repertoire)

    first_root = Line(
        repertoire_id=first_repertoire.id,
        parent_id=None,
        moves=['e2e4'],
    )
    second_root = Line(
        repertoire_id=second_repertoire.id,
        parent_id=None,
        moves=['d2d4'],
    )

    await line_repository.create(first_root)
    await line_repository.create(second_root)
    await session.flush()

    invalid_child = Line(
        repertoire_id=first_repertoire.id,
        parent_id=second_root.id,
        moves=['e7e5'],
    )

    session.add(invalid_child)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_child_parent_must_exist(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repertoire_repository = RepertoireRepository(session)

    await repertoire_repository.create(repertoire)

    root = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['e2e4'],
    )

    await LineRepository(session).create(root)
    await session.flush()

    child = Line(
        repertoire_id=repertoire.id,
        parent_id=uuid.uuid4(),
        moves=['e7e5'],
    )

    session.add(child)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_moves_cannot_be_empty(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repertoire_repository = RepertoireRepository(session)

    await repertoire_repository.create(repertoire)

    line = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=[],
    )

    session.add(line)

    with pytest.raises(IntegrityError):
        await session.flush()

    await session.rollback()


@pytest.mark.asyncio
async def test_deleting_repertoire_deletes_all_lines(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repertoire_repository = RepertoireRepository(session)
    line_repository = LineRepository(session)

    await repertoire_repository.create(repertoire)

    root = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['e2e4'],
    )

    await line_repository.create(root)

    child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await line_repository.create(child)

    grandchild = Line(
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['g1f3'],
    )

    await line_repository.create(grandchild)

    await session.commit()

    await repertoire_repository.delete(repertoire)
    await session.commit()

    result = await session.execute(
        text(
            'SELECT COUNT(*) FROM lines WHERE repertoire_id = :repertoire_id'
        ),
        {
            'repertoire_id': repertoire.id,
        },
    )

    assert result.scalar_one() == 0


@pytest.mark.asyncio
async def test_deleting_parent_deletes_subtree(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repertoire_repository = RepertoireRepository(session)
    line_repository = LineRepository(session)

    await repertoire_repository.create(repertoire)

    root = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['e2e4'],
    )

    await line_repository.create(root)

    child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await line_repository.create(child)

    grandchild = Line(
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['g1f3'],
    )

    await line_repository.create(grandchild)

    await session.commit()

    await line_repository.delete(child)
    await session.commit()

    result = await session.execute(
        text(
            'SELECT id FROM lines WHERE repertoire_id = :repertoire_id'
        ),
        {
            'repertoire_id': repertoire.id,
        },
    )

    remaining_ids = {row[0] for row in result}

    assert remaining_ids == {root.id}


@pytest.mark.asyncio
async def test_deleting_line_does_not_delete_other_branches(
        session: AsyncSession,
        ) -> None:
    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
    )

    repertoire_repository = RepertoireRepository(session)
    line_repository = LineRepository(session)

    await repertoire_repository.create(repertoire)

    root = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['e2e4'],
    )

    await line_repository.create(root)

    first_child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    second_child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['c7c5'],
    )

    await line_repository.create(first_child)
    await line_repository.create(second_child)
    await session.commit()

    await line_repository.delete(first_child)
    await session.commit()

    result = await line_repository.get_all_by_repertoire(
        repertoire.id,
    )

    assert {line.id for line in result} == {
        root.id,
        second_child.id,
    }
