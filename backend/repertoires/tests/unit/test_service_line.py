import uuid
from unittest.mock import AsyncMock, MagicMock

import chess
import pytest

from exceptions import (
    InvalidLineMovesError,
    InvalidLineRelationshipError,
    LineNotFoundError,
    ParentLineMovesUpdateError,
    RepertoireNotFoundError,
    RepertoireRevisionConflictError,
    RootLineDeletionError,
)
from models.line import Line
from models.repertoire import (
    Repertoire,
    RepertoireSide,
)
from schemas.line import (
    LineBatchCreate,
    LineBatchUpdate,
    LineCreate,
    LinePatchRequest,
    LineUpdate,
)
from services.line import LineService


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()

    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=False)

    session.begin.return_value = transaction
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()

    return session


@pytest.fixture
def service(
        session: MagicMock,
        ) -> LineService:
    service = LineService(session)

    service.line_repository.create = AsyncMock(
        side_effect=lambda line: line,
    )
    service.line_repository.delete = AsyncMock()
    service.line_repository.get_by_id_and_repertoire = AsyncMock()

    service.repertoire_repository.create = AsyncMock(
        side_effect=lambda repertoire: repertoire,
    )
    service.repertoire_repository.delete = AsyncMock()
    service.repertoire_repository.get_by_id_for_user = AsyncMock()
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock()

    service.line_repository.get_all_by_repertoire = AsyncMock()

    return service


@pytest.fixture
def repertoire() -> Repertoire:
    return Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Italian Game',
        description='',
        side=RepertoireSide.WHITE,
        revision=1,
    )


@pytest.fixture
def root(
        repertoire: Repertoire,
        ) -> Line:
    return Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=None,
        moves=['e2e4'],
        analytic_version=1,
        parent_analytic_version=None,
    )


@pytest.mark.asyncio
async def test_get_repertoire_returns_owned_repertoire(
        service: LineService,
        repertoire: Repertoire,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    result = await service._get_repertoire(
        repertoire.id,
        repertoire.user_id,
    )

    assert result is repertoire

    service.repertoire_repository.get_by_id_for_user.assert_awaited_once_with(
        repertoire.id,
        repertoire.user_id,
    )


@pytest.mark.asyncio
async def test_get_repertoire_raises_when_missing(
        service: LineService,
        ) -> None:
    repertoire_id = uuid.uuid4()
    user_id = uuid.uuid4()

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=None,
    )

    with pytest.raises(RepertoireNotFoundError):
        await service._get_repertoire(
            repertoire_id,
            user_id,
        )


@pytest.mark.asyncio
async def test_get_line_returns_line_from_repertoire(
        service: LineService,
        root: Line,
        ) -> None:
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )

    result = await service._get_line(
        root.repertoire_id,
        root.id,
    )

    assert result is root

    service.line_repository.get_by_id_and_repertoire.assert_awaited_once_with(
        root.id,
        root.repertoire_id,
    )


@pytest.mark.asyncio
async def test_get_line_raises_when_missing(
        service: LineService,
        ) -> None:
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=None,
    )

    with pytest.raises(LineNotFoundError):
        await service._get_line(
            uuid.uuid4(),
            uuid.uuid4(),
        )


def test_validate_move_count_accepts_odd_white_root() -> None:
    LineService._validate_move_count(
        ['e2e4'],
        RepertoireSide.WHITE,
        True,
    )


def test_validate_move_count_accepts_even_black_root() -> None:
    LineService._validate_move_count(
        ['e2e4', 'c7c5'],
        RepertoireSide.BLACK,
        True,
    )


def test_validate_move_count_accepts_even_non_root_line() -> None:
    LineService._validate_move_count(
        ['e7e5', 'g1f3'],
        RepertoireSide.WHITE,
        False,
    )


def test_validate_move_count_rejects_even_white_root() -> None:
    with pytest.raises(ValueError):
        LineService._validate_move_count(
            ['e2e4', 'e7e5'],
            RepertoireSide.WHITE,
            True,
        )


def test_validate_move_count_rejects_odd_black_root() -> None:
    with pytest.raises(ValueError):
        LineService._validate_move_count(
            ['e2e4'],
            RepertoireSide.BLACK,
            True,
        )


def test_validate_move_count_rejects_odd_non_root_line() -> None:
    with pytest.raises(ValueError):
        LineService._validate_move_count(
            ['e7e5'],
            RepertoireSide.WHITE,
            False,
        )


@pytest.mark.asyncio
async def test_get_tree_returns_root(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_root = AsyncMock(
        return_value=root,
    )

    result = await service.get_tree(
        repertoire.id,
        repertoire.user_id,
    )

    assert result is root


@pytest.mark.asyncio
async def test_get_tree_raises_when_root_missing(
        service: LineService,
        repertoire: Repertoire,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_root = AsyncMock(
        return_value=None,
    )

    with pytest.raises(LineNotFoundError):
        await service.get_tree(
            repertoire.id,
            repertoire.user_id,
        )


@pytest.mark.asyncio
async def test_get_tree_response_builds_tree(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    child = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5', 'g1f3'],
        analytic_version=2,
        parent_analytic_version=None,
    )

    grandchild = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['b8c6', 'f1c4'],
        analytic_version=3,
        parent_analytic_version=None,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_root = AsyncMock(
        return_value=root,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[
            root,
            child,
            grandchild,
        ],
    )

    result = await service.get_tree_response(
        repertoire.id,
        repertoire.user_id,
    )

    assert result == {
        'id': root.id,
        'tag': None,
        'moves': ['e2e4'],
        'analytic_version': 1,
        'children': [
            {
                'id': child.id,
                'tag': None,
                'moves': ['e7e5', 'g1f3'],
                'analytic_version': 2,
                'children': [
                    {
                        'id': grandchild.id,
                        'tag': None,
                        'moves': ['b8c6', 'f1c4'],
                        'analytic_version': 3,
                        'children': [],
                    },
                ],
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_line_response_returns_subtree(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    child = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5', 'g1f3'],
        analytic_version=2,
        parent_analytic_version=None,
    )

    grandchild = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['b8c6', 'f1c4'],
        analytic_version=3,
        parent_analytic_version=None,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=child,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[
            root,
            child,
            grandchild,
        ],
    )

    result = await service.get_line_response(
        repertoire.id,
        child.id,
        repertoire.user_id,
    )

    assert result == {
        'id': child.id,
        'tag': None,
        'moves': ['e7e5', 'g1f3'],
        'analytic_version': 2,
        'children': [
            {
                'id': grandchild.id,
                'tag': None,
                'moves': ['b8c6', 'f1c4'],
                'analytic_version': 3,
                'children': [],
            },
        ],
    }


@pytest.mark.asyncio
async def test_create_child_increments_revision_only(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )

    data = LineCreate(
        tag='Main line',
        moves=['e7e5', 'g1f3'],
    )

    result = await service.create_child(
        repertoire.id,
        root.id,
        repertoire.user_id,
        data,
    )

    assert result.repertoire_id == repertoire.id
    assert result.parent_id == root.id
    assert result.tag == 'Main line'
    assert result.moves == ['e7e5', 'g1f3']
    assert result.analytic_version == 1
    assert result.parent_analytic_version == root.analytic_version

    assert repertoire.revision == 2

    created_line = (
        service.line_repository.create
        .await_args
        .args[0]
    )

    assert created_line.parent_id == root.id
    assert created_line.repertoire_id == repertoire.id
    assert created_line.tag == 'Main line'
    assert created_line.moves == ['e7e5', 'g1f3']
    assert created_line.analytic_version == 1
    assert created_line.parent_analytic_version == root.analytic_version


@pytest.mark.asyncio
async def test_create_child_raises_when_repertoire_missing(
        service: LineService,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=None,
    )

    with pytest.raises(RepertoireNotFoundError):
        await service.create_child(
            uuid.uuid4(),
            uuid.uuid4(),
            uuid.uuid4(),
            LineCreate(
                moves=['e7e5', 'g1f3'],
            ),
        )

    service.line_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_child_rejects_illegal_moves(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )

    with pytest.raises(InvalidLineMovesError):
        await service.create_child(
            repertoire.id,
            root.id,
            repertoire.user_id,
            LineCreate(
                moves=['e7e6', 'e7e5'],
            ),
        )

    service.line_repository.create.assert_not_awaited()
    assert repertoire.revision == 1


@pytest.mark.asyncio
async def test_create_child_rejects_wrong_move_count(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )

    with pytest.raises(InvalidLineMovesError):
        await service.create_child(
            repertoire.id,
            root.id,
            repertoire.user_id,
            LineCreate(
                moves=['e7e5'],
            ),
        )

    service.line_repository.create.assert_not_awaited()
    assert repertoire.revision == 1


@pytest.mark.asyncio
async def test_update_tag_changes_revision_only(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )

    data = LineUpdate(
        tag='Updated',
    )

    result = await service.update(
        repertoire.id,
        root.id,
        repertoire.user_id,
        data,
    )

    assert result is root
    assert root.tag == 'Updated'
    assert root.analytic_version == 1
    assert root.parent_analytic_version is None
    assert repertoire.revision == 2


@pytest.mark.asyncio
async def test_update_leaf_moves_changes_revision_and_line_analytic_version(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )
    service.line_repository.has_children = AsyncMock(
        return_value=False,
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )

    data = LineUpdate(
        moves=['d2d4'],
    )

    result = await service.update(
        repertoire.id,
        root.id,
        repertoire.user_id,
        data,
    )

    assert result is root
    assert root.moves == ['d2d4']
    assert root.analytic_version == 2
    assert root.parent_analytic_version is None
    assert repertoire.revision == 2


@pytest.mark.asyncio
async def test_update_tag_and_moves_changes_versions_once(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )
    service.line_repository.has_children = AsyncMock(
        return_value=False,
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )

    data = LineUpdate(
        tag='Updated',
        moves=['d2d4'],
    )

    result = await service.update(
        repertoire.id,
        root.id,
        repertoire.user_id,
        data,
    )

    assert result is root
    assert root.tag == 'Updated'
    assert root.moves == ['d2d4']
    assert root.analytic_version == 2
    assert root.parent_analytic_version is None
    assert repertoire.revision == 2


@pytest.mark.asyncio
async def test_update_parent_moves_raises_error(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )
    service.line_repository.has_children = AsyncMock(
        return_value=True,
    )

    with pytest.raises(ParentLineMovesUpdateError):
        await service.update(
            repertoire.id,
            root.id,
            repertoire.user_id,
            LineUpdate(
                moves=['d2d4'],
            ),
        )

    assert root.moves == ['e2e4']
    assert root.analytic_version == 1
    assert root.parent_analytic_version is None
    assert repertoire.revision == 1


@pytest.mark.asyncio
async def test_update_rejects_illegal_leaf_moves(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )
    service.line_repository.has_children = AsyncMock(
        return_value=False,
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )

    with pytest.raises(InvalidLineMovesError):
        await service.update(
            repertoire.id,
            root.id,
            repertoire.user_id,
            LineUpdate(
                moves=['e2e5'],
            ),
        )

    assert root.moves == ['e2e4']
    assert root.analytic_version == 1
    assert root.parent_analytic_version is None
    assert repertoire.revision == 1


@pytest.mark.asyncio
async def test_update_raises_when_repertoire_missing(
        service: LineService,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=None,
    )

    with pytest.raises(RepertoireNotFoundError):
        await service.update(
            uuid.uuid4(),
            uuid.uuid4(),
            uuid.uuid4(),
            LineUpdate(
                tag='Test',
            ),
        )


@pytest.mark.asyncio
async def test_delete_child_increments_revision_only(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    child = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5', 'g1f3'],
        analytic_version=4,
        parent_analytic_version=None,
    )

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=child,
    )

    await service.delete(
        repertoire.id,
        child.id,
        repertoire.user_id,
    )

    service.line_repository.delete.assert_awaited_once_with(child)

    assert repertoire.revision == 2


@pytest.mark.asyncio
async def test_delete_root_raises_error(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        return_value=root,
    )

    with pytest.raises(RootLineDeletionError):
        await service.delete(
            repertoire.id,
            root.id,
            repertoire.user_id,
        )

    service.line_repository.delete.assert_not_awaited()

    assert repertoire.revision == 1


@pytest.mark.asyncio
async def test_delete_raises_when_repertoire_missing(
        service: LineService,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=None,
    )

    with pytest.raises(RepertoireNotFoundError):
        await service.delete(
            uuid.uuid4(),
            uuid.uuid4(),
            uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_patch_lines_updates_creates_and_deletes_atomically(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    updated_line = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        tag='Old',
        moves=['e7e5', 'g1f3'],
        analytic_version=3,
        parent_analytic_version=None,
    )

    deleted_line = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        tag='Deleted',
        moves=['c7c5', 'g1f3'],
        analytic_version=4,
        parent_analytic_version=None,
    )

    created_id = uuid.uuid4()

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[
            root,
            updated_line,
            deleted_line,
        ],
    )
    service.line_repository.get_by_id_and_repertoire = AsyncMock(
        side_effect=lambda line_id, repertoire_id: {
            root.id: root,
            updated_line.id: updated_line,
            deleted_line.id: deleted_line,
        }.get(line_id),
    )
    service.line_repository.get_path_to_root = AsyncMock(
        side_effect=lambda line_id, repertoire_id: [root, updated_line]
        if line_id == updated_line.id
        else [root],
    )
    service.line_repository.has_children = AsyncMock(
        return_value=False,
    )

    data = LinePatchRequest(
        revision=1,
        create=[
            LineBatchCreate(
                line_id=created_id,
                parent_id=root.id,
                tag='Created',
                moves=['e7e5', 'g1f3'],
            ),
        ],
        update=[
            LineBatchUpdate(
                line_id=updated_line.id,
                tag='Updated',
                moves=['d7d6', 'g1f3'],
            ),
        ],
        delete=[deleted_line.id],
    )

    result = await service.patch_lines(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert result == 2
    assert repertoire.revision == 2

    assert updated_line.tag == 'Updated'
    assert updated_line.moves == ['d7d6', 'g1f3']
    assert updated_line.analytic_version == 4
    assert updated_line.parent_analytic_version is None

    service.line_repository.delete.assert_awaited_once_with(
        deleted_line,
    )

    created_lines = [
        call.args[0]
        for call in service.line_repository.create.await_args_list
    ]

    assert len(created_lines) == 1
    assert created_lines[0].id == created_id
    assert created_lines[0].parent_id == root.id
    assert created_lines[0].tag == 'Created'
    assert created_lines[0].moves == ['e7e5', 'g1f3']
    assert created_lines[0].analytic_version == 1
    assert created_lines[0].parent_analytic_version == root.analytic_version


@pytest.mark.asyncio
async def test_patch_lines_updates_only_tag_without_changing_analytic_version(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    root.analytic_version = 5
    root.parent_analytic_version = 4

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root],
    )
    service.line_repository.has_children = AsyncMock(
        return_value=False,
    )

    data = LinePatchRequest(
        revision=1,
        update=[
            LineBatchUpdate(
                line_id=root.id,
                tag='Updated',
            ),
        ],
    )

    result = await service.patch_lines(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert result == 2
    assert repertoire.revision == 2
    assert root.tag == 'Updated'
    assert root.analytic_version == 5
    assert root.parent_analytic_version == 4


@pytest.mark.asyncio
async def test_patch_lines_updates_moves_and_increments_only_changed_line_version(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    root.analytic_version = 5
    root.parent_analytic_version = 4

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root],
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )
    service.line_repository.has_children = AsyncMock(
        return_value=False,
    )

    data = LinePatchRequest(
        revision=1,
        update=[
            LineBatchUpdate(
                line_id=root.id,
                moves=['d2d4'],
            ),
        ],
    )

    result = await service.patch_lines(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert result == 2
    assert repertoire.revision == 2
    assert root.moves == ['d2d4']
    assert root.analytic_version == 6
    assert root.parent_analytic_version == 4


@pytest.mark.asyncio
async def test_patch_lines_create_sets_parent_analytic_version(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    root.analytic_version = 7

    created_id = uuid.uuid4()

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root],
    )
    service.line_repository.get_path_to_root = AsyncMock(
        return_value=[root],
    )

    data = LinePatchRequest(
        revision=1,
        create=[
            LineBatchCreate(
                line_id=created_id,
                parent_id=root.id,
                moves=['e7e5', 'g1f3'],
            ),
        ],
    )

    result = await service.patch_lines(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert result == 2

    created_line = (
        service.line_repository.create
        .await_args
        .args[0]
    )

    assert created_line.analytic_version == 1
    assert created_line.parent_analytic_version == root.analytic_version


@pytest.mark.asyncio
async def test_patch_lines_delete_does_not_change_revisions_of_other_lines(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    child = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5', 'g1f3'],
        analytic_version=8,
        parent_analytic_version=7,
    )

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root, child],
    )

    data = LinePatchRequest(
        revision=1,
        delete=[child.id],
    )

    result = await service.patch_lines(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert result == 2
    assert repertoire.revision == 2
    assert child.analytic_version == 8
    assert child.parent_analytic_version == 7

    service.line_repository.delete.assert_awaited_once_with(child)


@pytest.mark.asyncio
async def test_patch_lines_rejects_revision_conflict(
        service: LineService,
        repertoire: Repertoire,
        ) -> None:
    repertoire.revision = 2

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )

    data = LinePatchRequest(
        revision=1,
        update=[
            LineBatchUpdate(
                line_id=uuid.uuid4(),
                tag='Updated',
            ),
        ],
    )

    with pytest.raises(RepertoireRevisionConflictError):
        await service.patch_lines(
            repertoire.id,
            repertoire.user_id,
            data,
        )

    service.line_repository.get_all_by_repertoire.assert_not_awaited()


@pytest.mark.asyncio
async def test_patch_lines_rejects_update_of_parent_moves(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root],
    )
    service.line_repository.has_children = AsyncMock(
        return_value=True,
    )

    data = LinePatchRequest(
        revision=1,
        update=[
            LineBatchUpdate(
                line_id=root.id,
                moves=['d2d4'],
            ),
        ],
    )

    with pytest.raises(ParentLineMovesUpdateError):
        await service.patch_lines(
            repertoire.id,
            repertoire.user_id,
            data,
        )

    assert repertoire.revision == 1
    assert root.analytic_version == 1


@pytest.mark.asyncio
async def test_patch_lines_rejects_deleting_root(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root],
    )

    data = LinePatchRequest(
        revision=1,
        delete=[root.id],
    )

    with pytest.raises(RootLineDeletionError):
        await service.patch_lines(
            repertoire.id,
            repertoire.user_id,
            data,
        )

    service.line_repository.delete.assert_not_awaited()
    assert repertoire.revision == 1


@pytest.mark.asyncio
async def test_patch_lines_rejects_missing_updated_line(
        service: LineService,
        repertoire: Repertoire,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[],
    )

    data = LinePatchRequest(
        revision=1,
        update=[
            LineBatchUpdate(
                line_id=uuid.uuid4(),
                tag='Updated',
            ),
        ],
    )

    with pytest.raises(LineNotFoundError):
        await service.patch_lines(
            repertoire.id,
            repertoire.user_id,
            data,
        )


@pytest.mark.asyncio
async def test_patch_lines_rejects_missing_deleted_line(
        service: LineService,
        repertoire: Repertoire,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[],
    )

    data = LinePatchRequest(
        revision=1,
        delete=[uuid.uuid4()],
    )

    with pytest.raises(LineNotFoundError):
        await service.patch_lines(
            repertoire.id,
            repertoire.user_id,
            data,
        )


@pytest.mark.asyncio
async def test_patch_lines_rejects_invalid_create_parent(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root],
    )

    data = LinePatchRequest(
        revision=1,
        create=[
            LineBatchCreate(
                line_id=uuid.uuid4(),
                parent_id=uuid.uuid4(),
                moves=['e7e5', 'g1f3'],
            ),
        ],
    )

    with pytest.raises(InvalidLineRelationshipError):
        await service.patch_lines(
            repertoire.id,
            repertoire.user_id,
            data,
        )


@pytest.mark.asyncio
async def test_patch_lines_rejects_create_update_same_line_id(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    line_id = uuid.uuid4()

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[root],
    )

    data = LinePatchRequest(
        revision=1,
        create=[
            LineBatchCreate(
                line_id=line_id,
                parent_id=root.id,
                moves=['e7e5', 'g1f3'],
            ),
        ],
        update=[
            LineBatchUpdate(
                line_id=line_id,
                tag='Updated',
            ),
        ],
    )

    with pytest.raises(InvalidLineRelationshipError):
        await service.patch_lines(
            repertoire.id,
            repertoire.user_id,
            data,
        )
