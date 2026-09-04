import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.repertoire import (
    Line,
    Repertoire,
    RepertoireSide,
)
from repositories.line import LineRepository
from repositories.repertoire import RepertoireRepository


@pytest_asyncio.fixture
async def repertoire(
        session: AsyncSession,
        ) -> Repertoire:
    repository = RepertoireRepository(session)

    repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Test repertoire',
        description='',
        side=RepertoireSide.WHITE,
    )

    await repository.create(repertoire)

    root = Line(
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['e2e4'],
    )

    session.add(root)
    await session.commit()

    return repertoire


@pytest.mark.asyncio
async def test_create_and_get_by_id(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    line = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await repository.create(line)
    await session.commit()

    result = await repository.get_by_id(line.id)

    assert result is not None
    assert result.id == line.id
    assert result.repertoire_id == repertoire.id
    assert result.moves == ['e7e5']


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing_line(
        session: AsyncSession,
        ) -> None:
    repository = LineRepository(session)

    result = await repository.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_and_repertoire_returns_line(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    line = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await repository.create(line)
    await session.commit()

    result = await repository.get_by_id_and_repertoire(
        line.id,
        repertoire.id,
    )

    assert result is not None
    assert result.id == line.id


@pytest.mark.asyncio
async def test_get_by_id_and_repertoire_rejects_other_repertoire(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    line = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await repository.create(line)
    await session.commit()

    result = await repository.get_by_id_and_repertoire(
        line.id,
        uuid.uuid4(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_root_returns_root(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    result = await repository.get_root(repertoire.id)

    assert result is not None
    assert result.parent_id is None
    assert result.repertoire_id == repertoire.id


@pytest.mark.asyncio
async def test_get_root_returns_none_for_missing_repertoire(
        session: AsyncSession,
        ) -> None:
    repository = LineRepository(session)

    result = await repository.get_root(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_all_by_repertoire_returns_all_lines(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await repository.create(child)

    grandchild = Line(
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['g1f3'],
    )

    await repository.create(grandchild)
    await session.commit()

    result = await repository.get_all_by_repertoire(
        repertoire.id,
    )

    assert len(result) == 3
    assert {line.id for line in result} == {
        root.id,
        child.id,
        grandchild.id,
    }


@pytest.mark.asyncio
async def test_get_all_by_repertoire_does_not_return_other_repertoire_lines(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repertoire_repository = RepertoireRepository(session)
    line_repository = LineRepository(session)

    other_repertoire = Repertoire(
        user_id=uuid.uuid4(),
        name='Other repertoire',
        description='',
        side=RepertoireSide.BLACK,
    )

    await repertoire_repository.create(other_repertoire)

    other_root = Line(
        repertoire_id=other_repertoire.id,
        parent_id=None,
        moves=['e2e4', 'e7e5'],
    )

    await line_repository.create(other_root)
    await session.commit()

    result = await line_repository.get_all_by_repertoire(
        repertoire.id,
    )

    assert len(result) == 1
    assert result[0].repertoire_id == repertoire.id


@pytest.mark.asyncio
async def test_get_path_to_root_returns_path_in_root_to_child_order(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await repository.create(child)

    grandchild = Line(
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['g1f3'],
    )

    await repository.create(grandchild)
    await session.commit()

    result = await repository.get_path_to_root(
        grandchild.id,
        repertoire.id,
    )

    assert [line.id for line in result] == [
        root.id,
        child.id,
        grandchild.id,
    ]


@pytest.mark.asyncio
async def test_get_path_to_root_returns_single_line_for_root(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    result = await repository.get_path_to_root(
        root.id,
        repertoire.id,
    )

    assert [line.id for line in result] == [root.id]


@pytest.mark.asyncio
async def test_get_path_to_root_returns_empty_for_missing_line(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    result = await repository.get_path_to_root(
        uuid.uuid4(),
        repertoire.id,
    )

    assert result == []


@pytest.mark.asyncio
async def test_has_children_returns_true_when_children_exist(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await repository.create(child)
    await session.commit()

    result = await repository.has_children(root.id)

    assert result is True


@pytest.mark.asyncio
async def test_has_children_returns_false_for_leaf(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    result = await repository.has_children(root.id)

    assert result is False


@pytest.mark.asyncio
async def test_delete_removes_line(
        session: AsyncSession,
        repertoire: Repertoire,
        ) -> None:
    repository = LineRepository(session)

    root = await repository.get_root(repertoire.id)

    assert root is not None

    child = Line(
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5'],
    )

    await repository.create(child)
    await session.commit()

    await repository.delete(child)
    await session.commit()

    result = await repository.get_by_id(child.id)

    assert result is None
