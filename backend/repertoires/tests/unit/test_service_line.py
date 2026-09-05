import uuid
from unittest.mock import AsyncMock, MagicMock

import chess
import pytest

from exceptions import (
    InvalidLineMovesError,
    LineNotFoundError,
    ParentLineMovesUpdateError,
    RepertoireNotFoundError,
    RepertoireVersionConflictError,
    RootLineDeletionError,
)
from models.repertoire import (
    Line,
    Repertoire,
    RepertoireSide,
)
from schemas.line import (
    LineCreate,
    LineTreeReplace,
    LineTreeReplaceRequest,
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
    service.line_repository.get_path_to_root = AsyncMock()
    service.line_repository.get_root = AsyncMock()
    service.line_repository.get_all_by_repertoire = AsyncMock()
    service.line_repository.has_children = AsyncMock()

    service.repertoire_repository.create = AsyncMock(
        side_effect=lambda repertoire: repertoire,
    )
    service.repertoire_repository.delete = AsyncMock()
    service.repertoire_repository.get_by_id_for_user = AsyncMock()
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock()
    service.repertoire_repository.update_version = AsyncMock(
        return_value=True,
    )

    return service


@pytest.fixture
def repertoire() -> Repertoire:
    return Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Italian Game',
        description='',
        side=RepertoireSide.WHITE,
        version=1,
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


def test_validate_tree_accepts_valid_white_tree(
        service: LineService,
        ) -> None:
    tree = LineTreeReplace(
        moves=['e2e4'],
        children=[
            LineTreeReplace(
                moves=['e7e5', 'g1f3'],
            ),
        ],
    )

    service._validate_tree(
        tree,
        chess.Board(),
        RepertoireSide.WHITE,
        True,
    )


def test_validate_tree_accepts_valid_black_tree(
        service: LineService,
        ) -> None:
    tree = LineTreeReplace(
        moves=['e2e4', 'c7c5'],
        children=[
            LineTreeReplace(
                moves=['g1f3', 'd7d6'],
            ),
        ],
    )

    service._validate_tree(
        tree,
        chess.Board(),
        RepertoireSide.BLACK,
        True,
    )


def test_validate_tree_rejects_illegal_move(
        service: LineService,
        ) -> None:
    tree = LineTreeReplace(
        moves=['e2e5'],
    )

    with pytest.raises(InvalidLineMovesError):
        service._validate_tree(
            tree,
            chess.Board(),
            RepertoireSide.WHITE,
            True,
        )


def test_validate_tree_rejects_wrong_move_count(
        service: LineService,
        ) -> None:
    tree = LineTreeReplace(
        moves=['e2e4', 'e7e5'],
    )

    with pytest.raises(InvalidLineMovesError):
        service._validate_tree(
            tree,
            chess.Board(),
            RepertoireSide.WHITE,
            True,
        )


def test_validate_tree_validates_child_from_parent_position(
        service: LineService,
        ) -> None:
    tree = LineTreeReplace(
        moves=['e2e4'],
        children=[
            LineTreeReplace(
                moves=['e7e5', 'g1f3'],
            ),
        ],
    )

    service._validate_tree(
        tree,
        chess.Board(),
        RepertoireSide.WHITE,
        True,
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
    )

    grandchild = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['b8c6', 'f1c4'],
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
        'children': [
            {
                'id': child.id,
                'tag': None,
                'moves': ['e7e5', 'g1f3'],
                'children': [
                    {
                        'id': grandchild.id,
                        'tag': None,
                        'moves': ['b8c6', 'f1c4'],
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
    )

    grandchild = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=child.id,
        moves=['b8c6', 'f1c4'],
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
        'children': [
            {
                'id': grandchild.id,
                'tag': None,
                'moves': ['b8c6', 'f1c4'],
                'children': [],
            },
        ],
    }


@pytest.mark.asyncio
async def test_create_child_creates_line_and_increments_version(
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
    assert repertoire.version == 2

    service.line_repository.create.assert_awaited_once()

    created_line = (
        service.line_repository.create
        .await_args
        .args[0]
    )

    assert created_line.parent_id == root.id
    assert created_line.repertoire_id == repertoire.id
    assert created_line.tag == 'Main line'
    assert created_line.moves == ['e7e5', 'g1f3']


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
    assert repertoire.version == 1


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
    assert repertoire.version == 1


@pytest.mark.asyncio
async def test_update_tag(
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
    assert repertoire.version == 2


@pytest.mark.asyncio
async def test_update_leaf_moves(
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
    assert repertoire.version == 2


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
    assert repertoire.version == 1


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
    assert repertoire.version == 1


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
async def test_delete_child_deletes_line_and_increments_version(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    child = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5', 'g1f3'],
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
    assert repertoire.version == 2


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
    assert repertoire.version == 1


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
async def test_replace_tree_replaces_existing_children(
        service: LineService,
        session: MagicMock,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    old_child = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        moves=['e7e5', 'g1f3'],
    )

    new_tree = LineTreeReplace(
        tag='New root',
        moves=['d2d4'],
        children=[
            LineTreeReplace(
                tag='New child',
                moves=['d7d5', 'c2c4'],
            ),
        ],
    )

    request = LineTreeReplaceRequest(
        version=1,
        tree=new_tree,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_root = AsyncMock(
        return_value=root,
    )
    service.line_repository.get_all_by_repertoire = AsyncMock(
        return_value=[
            root,
            old_child,
        ],
    )

    await service.replace_tree(
        repertoire.id,
        repertoire.user_id,
        request,
    )

    assert root.tag == 'New root'
    assert root.moves == ['d2d4']
    assert repertoire.version == 2

    session.delete.assert_awaited_once_with(old_child)
    service.line_repository.create.assert_awaited_once()

    created_child = (
        service.line_repository.create
        .await_args
        .args[0]
    )

    assert created_child.parent_id == root.id
    assert created_child.tag == 'New child'
    assert created_child.moves == ['d7d5', 'c2c4']


@pytest.mark.asyncio
async def test_replace_tree_rejects_missing_repertoire(
        service: LineService,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=None,
    )

    request = LineTreeReplaceRequest(
        version=1,
        tree=LineTreeReplace(
            moves=['e2e4'],
        ),
    )

    with pytest.raises(RepertoireNotFoundError):
        await service.replace_tree(
            uuid.uuid4(),
            uuid.uuid4(),
            request,
        )


@pytest.mark.asyncio
async def test_replace_tree_rejects_version_conflict(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    repertoire.version = 2

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )

    request = LineTreeReplaceRequest(
        version=1,
        tree=LineTreeReplace(
            moves=['e2e4'],
        ),
    )

    with pytest.raises(RepertoireVersionConflictError):
        await service.replace_tree(
            repertoire.id,
            repertoire.user_id,
            request,
        )

    service.line_repository.get_root.assert_not_awaited()
    service.line_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_replace_tree_rejects_invalid_tree_before_transaction(
        service: LineService,
        repertoire: Repertoire,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    request = LineTreeReplaceRequest(
        version=1,
        tree=LineTreeReplace(
            moves=['e2e5'],
        ),
    )

    with pytest.raises(InvalidLineMovesError):
        await service.replace_tree(
            repertoire.id,
            repertoire.user_id,
            request,
        )

    service.repertoire_repository.get_by_id_for_user_for_update.assert_not_awaited()
    service.line_repository.get_root.assert_not_awaited()
    service.line_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_replace_tree_creates_root_when_root_missing(
        service: LineService,
        repertoire: Repertoire,
        ) -> None:
    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )
    service.line_repository.get_root = AsyncMock(
        return_value=None,
    )

    request = LineTreeReplaceRequest(
        version=1,
        tree=LineTreeReplace(
            tag='New root',
            moves=['e2e4'],
        ),
    )

    await service.replace_tree(
        repertoire.id,
        repertoire.user_id,
        request,
    )

    assert repertoire.version == 2
    service.line_repository.create.assert_awaited_once()

    created_root = (
        service.line_repository.create
        .await_args
        .args[0]
    )

    assert created_root.repertoire_id == repertoire.id
    assert created_root.parent_id is None
    assert created_root.tag == 'New root'
    assert created_root.moves == ['e2e4']


@pytest.mark.asyncio
async def test_create_children_recursive_creates_nested_tree(
        service: LineService,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    children = [
        LineTreeReplace(
            tag='First',
            moves=['e7e5', 'g1f3'],
            children=[
                LineTreeReplace(
                    tag='Nested',
                    moves=['b8c6', 'f1c4'],
                ),
            ],
        ),
    ]

    await service._create_children_recursive(
        repertoire.id,
        root.id,
        children,
    )

    assert service.line_repository.create.await_count == 2

    first_child = (
        service.line_repository.create
        .await_args_list[0]
        .args[0]
    )
    nested_child = (
        service.line_repository.create
        .await_args_list[1]
        .args[0]
    )

    assert first_child.parent_id == root.id
    assert first_child.tag == 'First'
    assert first_child.moves == ['e7e5', 'g1f3']

    assert nested_child.parent_id == first_child.id
    assert nested_child.tag == 'Nested'
    assert nested_child.moves == ['b8c6', 'f1c4']
