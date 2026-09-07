import uuid

import chess
from sqlalchemy.ext.asyncio import AsyncSession

from domains.chess_validator import ChessValidator
from exceptions import (
    InvalidLineMovesError,
    InvalidLineRelationshipError,
    LineNotFoundError,
    ParentLineMovesUpdateError,
    RepertoireNotFoundError,
    RepertoireRevisionConflictError,
    RootLineAlreadyExistsError,
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
    LineBatchCreate,
    LineCreate,
    LinePatchRequest,
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

    async def _validate_new_line_moves(
            self,
            repertoire_side: RepertoireSide,
            repertoire_id: uuid.UUID,
            parent: Line | None,
            moves: list[str],
            ) -> None:
        board = chess.Board()

        if parent is not None:
            path = await self.line_repository.get_path_to_root(
                parent.id,
                repertoire_id,
            )

            for current_line in path:
                self.chess_validator.apply_persisted_moves(
                    board,
                    current_line.moves,
                )

        self._validate_moves(
            board,
            moves,
            repertoire_side,
            parent is None,
        )

    @staticmethod
    def _validate_batch_ids(
            data: LinePatchRequest,
            existing_ids: set[uuid.UUID],
            ) -> None:
        create_ids = [item.line_id for item in data.create]
        update_ids = [item.line_id for item in data.update]
        delete_ids = data.delete

        if len(create_ids) != len(set(create_ids)):
            raise InvalidLineRelationshipError

        if len(update_ids) != len(set(update_ids)):
            raise InvalidLineRelationshipError

        if len(delete_ids) != len(set(delete_ids)):
            raise InvalidLineRelationshipError

        create_set = set(create_ids)
        update_set = set(update_ids)
        delete_set = set(delete_ids)

        if create_set & update_set:
            raise InvalidLineRelationshipError

        if create_set & delete_set:
            raise InvalidLineRelationshipError

        if update_set & delete_set:
            raise InvalidLineRelationshipError

        if create_set & existing_ids:
            raise InvalidLineRelationshipError

        if not update_set <= existing_ids:
            raise LineNotFoundError

        if not delete_set <= existing_ids:
            raise LineNotFoundError

    @staticmethod
    def _validate_delete_tree(
            lines_by_id: dict[uuid.UUID, Line],
            delete_ids: set[uuid.UUID],
            ) -> None:
        for line_id in delete_ids:
            current = lines_by_id[line_id].parent_id

            while current is not None:
                if current in delete_ids:
                    raise InvalidLineRelationshipError

                parent = lines_by_id.get(current)

                if parent is None:
                    break

                current = parent.parent_id

    @staticmethod
    def _validate_create_relationships(
            items: list[LineBatchCreate],
            existing_lines: dict[uuid.UUID, Line],
            delete_ids: set[uuid.UUID],
            ) -> None:
        create_ids = {item.line_id for item in items}

        for item in items:
            if item.parent_id is None:
                continue

            if item.parent_id in delete_ids:
                raise InvalidLineRelationshipError

            if (
                item.parent_id not in existing_lines
                and item.parent_id not in create_ids
            ):
                raise InvalidLineRelationshipError

            if item.parent_id == item.line_id:
                raise InvalidLineRelationshipError

    @staticmethod
    def _validate_create_update_conflicts(
            data: LinePatchRequest,
            ) -> None:
        update_move_ids = {
            item.line_id
            for item in data.update
            if item.moves is not None
        }

        create_parent_ids = {
            item.parent_id
            for item in data.create
            if item.parent_id is not None
        }

        if update_move_ids & create_parent_ids:
            raise ParentLineMovesUpdateError

    async def _create_batch_lines(
            self,
            repertoire_id: uuid.UUID,
            repertoire_side: RepertoireSide,
            items: list[LineBatchCreate],
            existing_lines: dict[uuid.UUID, Line],
            ) -> None:
        pending = list(items)
        created_ids: set[uuid.UUID] = set()

        while pending:
            progress = False
            next_pending: list[LineBatchCreate] = []

            for data in pending:
                parent: Line | None = None

                if data.parent_id is not None:
                    if data.parent_id in created_ids:
                        parent = await self._get_line(
                            repertoire_id,
                            data.parent_id,
                        )
                    elif data.parent_id in existing_lines:
                        parent = existing_lines[data.parent_id]
                    else:
                        next_pending.append(data)
                        continue

                await self._validate_new_line_moves(
                    repertoire_side,
                    repertoire_id,
                    parent,
                    data.moves,
                )

                if parent is None:
                    existing_root = await self.line_repository.get_root(
                        repertoire_id,
                    )

                    if existing_root is not None:
                        raise RootLineAlreadyExistsError

                line = Line(
                    id=data.line_id,
                    repertoire_id=repertoire_id,
                    parent_id=data.parent_id,
                    tag=data.tag,
                    moves=data.moves,
                    analytic_version=1,
                    parent_analytic_version=None,
                )

                await self.line_repository.create(line)

                existing_lines[line.id] = line
                created_ids.add(line.id)
                progress = True

            if not progress:
                raise InvalidLineRelationshipError

            pending = next_pending

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
                parent_analytic_version=None,
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

    async def patch_lines(
            self,
            repertoire_id: uuid.UUID,
            user_id: uuid.UUID,
            data: LinePatchRequest,
            ) -> int:
        async with self.session.begin():
            repertoire = await self.repertoire_repository.get_by_id_for_user_for_update(
                repertoire_id,
                user_id,
            )

            if repertoire is None:
                raise RepertoireNotFoundError

            if repertoire.revision != data.revision:
                raise RepertoireRevisionConflictError

            existing_lines_list = (
                await self.line_repository.get_all_by_repertoire(
                    repertoire_id,
                )
            )
            existing_lines = {
                line.id: line
                for line in existing_lines_list
            }
            existing_ids = set(existing_lines)

            self._validate_batch_ids(
                data,
                existing_ids,
            )

            delete_ids = set(data.delete)

            self._validate_delete_tree(
                existing_lines,
                delete_ids,
            )

            self._validate_create_relationships(
                data.create,
                existing_lines,
                delete_ids,
            )

            self._validate_create_update_conflicts(data)

            update_lines = {
                item.line_id: existing_lines[item.line_id]
                for item in data.update
            }

            for line in update_lines.values():
                if line.parent_id is None and line.id in delete_ids:
                    raise RootLineDeletionError

                has_children = await self.line_repository.has_children(
                    line.id,
                )

                if (
                    has_children
                    and any(
                        item.line_id == line.id
                        and item.moves is not None
                        for item in data.update
                    )
                ):
                    raise ParentLineMovesUpdateError

            for item in data.update:
                line = update_lines[item.line_id]
                fields = item.model_dump(
                    exclude_unset=True,
                )

                if 'tag' in fields:
                    line.tag = fields['tag']

                if 'moves' in fields:
                    await self._validate_line_moves(
                        repertoire.side,
                        repertoire_id,
                        line,
                        fields['moves'],
                    )

                    line.moves = fields['moves']
                    line.analytic_version += 1

            await self._create_batch_lines(
                repertoire_id,
                repertoire.side,
                data.create,
                existing_lines,
            )

            for line_id in data.delete:
                line = existing_lines[line_id]

                if line.parent_id is None:
                    raise RootLineDeletionError

                await self.line_repository.delete(line)

            repertoire.revision += 1

        return repertoire.revision
