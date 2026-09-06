import uuid

import chess
from sqlalchemy.ext.asyncio import AsyncSession

from domains.chess_validator import ChessValidator
from exceptions import (
    InvalidLineMovesError,
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
from repositories.line import LineRepository
from repositories.repertoire import RepertoireRepository
from schemas.line import (
    LineCreate,
    LineTreeReplace,
    LineTreeReplaceRequest,
    LineUpdate,
)


class LineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.line_repository = LineRepository(session)
        self.repertoire_repository = RepertoireRepository(session)
        self.chess_validator = ChessValidator()

    async def _get_repertoire(
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

    async def _get_line(
            self,
            repertoire_id: uuid.UUID,
            line_id: uuid.UUID,
            ) -> Line:
        line = await self.line_repository.get_by_id_and_repertoire(
            line_id,
            repertoire_id,
        )

        if line is None:
            raise LineNotFoundError

        return line

    @staticmethod
    def _build_subtree(
            line: Line,
            lines_by_parent: dict[uuid.UUID, list[Line]],
            ) -> dict[str, object]:
        children = lines_by_parent.get(line.id, [])

        return {
            'id': line.id,
            'tag': line.tag,
            'moves': line.moves,
            'analytic_version': line.analytic_version,
            'children': [
                LineService._build_subtree(
                    child,
                    lines_by_parent,
                )
                for child in children
            ],
        }

    @staticmethod
    def _validate_move_count(
            moves: list[str],
            side: RepertoireSide,
            is_root: bool,
            ) -> None:
        if is_root:
            if side == RepertoireSide.WHITE and len(moves) % 2 == 0:
                raise ValueError(
                    'White repertoire root must contain an odd number of moves.',
                )

            if side == RepertoireSide.BLACK and len(moves) % 2 != 0:
                raise ValueError(
                    'Black repertoire root must contain an even number of moves.',
                )

            return

        if len(moves) % 2 != 0:
            raise ValueError(
                'Non-root line must contain an even number of moves.',
            )

    def _validate_moves(
            self,
            board: chess.Board,
            moves: list[str],
            side: RepertoireSide,
            is_root: bool,
            ) -> None:
        try:
            self._validate_move_count(
                moves,
                side,
                is_root,
            )

            self.chess_validator.validate_moves(
                board,
                moves,
            )
        except ValueError as error:
            raise InvalidLineMovesError from error

    async def _validate_line_moves(
            self,
            repertoire_side: RepertoireSide,
            repertoire_id: uuid.UUID,
            line: Line,
            moves: list[str],
            ) -> None:
        path = await self.line_repository.get_path_to_root(
            line.id,
            repertoire_id,
        )

        board = chess.Board()

        for current_line in path[:-1]:
            self.chess_validator.apply_persisted_moves(
                board,
                current_line.moves,
            )

        self._validate_moves(
            board,
            moves,
            repertoire_side,
            line.parent_id is None,
        )

    def _validate_tree(
            self,
            node: LineTreeReplace,
            board: chess.Board,
            side: RepertoireSide,
            is_root: bool,
            ) -> None:
        current_board = board.copy()

        self._validate_moves(
            current_board,
            node.moves,
            side,
            is_root,
        )

        for child in node.children:
            self._validate_tree(
                child,
                current_board,
                side,
                False,
            )

    async def get_tree(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> Line:
        await self._get_repertoire(
            repertoire_id,
            user_id,
        )

        root = await self.line_repository.get_root(
            repertoire_id,
        )

        if root is None:
            raise LineNotFoundError

        return root

    async def get_tree_response(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> dict[str, object]:
        root = await self.get_tree(
            repertoire_id,
            user_id,
        )

        lines = await self.line_repository.get_all_by_repertoire(
            repertoire_id,
        )

        lines_by_parent: dict[uuid.UUID, list[Line]] = {}

        for line in lines:
            if line.parent_id is not None:
                lines_by_parent.setdefault(
                    line.parent_id,
                    [],
                ).append(line)

        return self._build_subtree(
            root,
            lines_by_parent,
        )

    async def get_line_response(
            self,
            repertoire_id: uuid.UUID,
            line_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> dict[str, object]:
        await self._get_repertoire(
            repertoire_id,
            user_id,
        )

        line = await self._get_line(
            repertoire_id,
            line_id,
        )

        lines = await self.line_repository.get_all_by_repertoire(
            repertoire_id,
        )

        lines_by_parent: dict[uuid.UUID, list[Line]] = {}

        for current_line in lines:
            if current_line.parent_id is not None:
                lines_by_parent.setdefault(
                    current_line.parent_id,
                    [],
                ).append(current_line)

        return self._build_subtree(
            line,
            lines_by_parent,
        )

    async def create_child(
            self,
            repertoire_id: uuid.UUID,
            parent_id: uuid.UUID,
            user_id: uuid.UUID,
            data: LineCreate,
            ) -> Line:
        async with self.session.begin():
            repertoire = await self.repertoire_repository.get_by_id_for_user_for_update(
                repertoire_id,
                user_id,
            )

            if repertoire is None:
                raise RepertoireNotFoundError

            parent = await self._get_line(
                repertoire_id,
                parent_id,
            )

            path = await self.line_repository.get_path_to_root(
                parent.id,
                repertoire_id,
            )

            board = chess.Board()

            for line in path:
                self.chess_validator.apply_persisted_moves(
                    board,
                    line.moves,
                )

            self._validate_moves(
                board,
                data.moves,
                repertoire.side,
                False,
            )

            line = Line(
                repertoire_id=repertoire_id,
                parent_id=parent_id,
                tag=data.tag,
                moves=data.moves,
                analytic_version=1,
            )

            await self.line_repository.create(line)

            repertoire.revision += 1

        return line

    async def update(
            self,
            repertoire_id: uuid.UUID,
            line_id: uuid.UUID,
            user_id: uuid.UUID,
            data: LineUpdate,
            ) -> Line:
        async with self.session.begin():
            repertoire = await self.repertoire_repository.get_by_id_for_user_for_update(
                repertoire_id,
                user_id,
            )

            if repertoire is None:
                raise RepertoireNotFoundError

            line = await self._get_line(
                repertoire_id,
                line_id,
            )

            fields = data.model_dump(exclude_unset=True)

            if 'tag' in fields:
                line.tag = fields['tag']

            if 'moves' in fields:
                has_children = await self.line_repository.has_children(
                    line.id,
                )

                if has_children:
                    raise ParentLineMovesUpdateError

                await self._validate_line_moves(
                    repertoire.side,
                    repertoire_id,
                    line,
                    fields['moves'],
                )

                line.moves = fields['moves']
                line.analytic_version += 1

            repertoire.revision += 1

        return line

    async def delete(
            self,
            repertoire_id: uuid.UUID,
            line_id: uuid.UUID,
            user_id: uuid.UUID,
            ) -> None:
        async with self.session.begin():
            repertoire = await self.repertoire_repository.get_by_id_for_user_for_update(
                repertoire_id,
                user_id,
            )

            if repertoire is None:
                raise RepertoireNotFoundError

            line = await self._get_line(
                repertoire_id,
                line_id,
            )

            if line.parent_id is None:
                raise RootLineDeletionError

            await self.line_repository.delete(line)

            repertoire.revision += 1

    async def replace_tree(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            data: LineTreeReplaceRequest,
            ) -> None:
        repertoire = await self.repertoire_repository.get_by_id_for_user(
            repertoire_id,
            user_id,
        )

        if repertoire is None:
            raise RepertoireNotFoundError

        self._validate_tree(
            data.tree,
            chess.Board(),
            repertoire.side,
            True,
        )

        async with self.session.begin():
            repertoire = await self.repertoire_repository.get_by_id_for_user_for_update(
                repertoire_id,
                user_id,
            )

            if repertoire is None:
                raise RepertoireNotFoundError

            if repertoire.revision != data.revision:
                raise RepertoireRevisionConflictError

            root = await self.line_repository.get_root(
                repertoire_id,
            )

            if root is None:
                root = Line(
                    repertoire_id=repertoire_id,
                    parent_id=None,
                    tag=data.tree.tag,
                    moves=data.tree.moves,
                    analytic_version=1,
                )

                await self.line_repository.create(root)

                await self._create_children_recursive(
                    repertoire_id,
                    root.id,
                    data.tree.children,
                )

            else:
                existing_lines = await self.line_repository.get_all_by_repertoire(
                    repertoire_id,
                )

                for line in existing_lines:
                    if line.id != root.id:
                        await self.session.delete(line)

                root.tag = data.tree.tag
                root.moves = data.tree.moves

                await self.session.flush()

                await self._create_children_recursive(
                    repertoire_id,
                    root.id,
                    data.tree.children,
                )

            repertoire.revision += 1
            repertoire.analytic_version += 1

    async def _create_children_recursive(
            self,
            repertoire_id: uuid.UUID,
            parent_id: uuid.UUID,
            children: list[LineTreeReplace],
            ) -> None:
        for child_data in children:
            child = Line(
                repertoire_id=repertoire_id,
                parent_id=parent_id,
                tag=child_data.tag,
                moves=child_data.moves,
                analytic_version=1,
            )

            await self.line_repository.create(child)

            await self._create_children_recursive(
                repertoire_id,
                child.id,
                child_data.children,
            )
