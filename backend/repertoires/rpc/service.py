from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

import grpc
from sqlalchemy import select

from db.session import AsyncSessionFactory
from grpc_gen.repertoire.v1 import repertoire_pb2, repertoire_pb2_grpc
from models.line import Line
from models.repertoire import Repertoire


class RepertoireGrpcService(
        repertoire_pb2_grpc.RepertoireServiceServicer,
        ):

    async def GetTrainingTree(
            self,
            request: Any,
            context: grpc.aio.ServicerContext[Any, Any],
            ) -> Any:

        try:
            user_id = uuid.UUID(request.user_id)
            repertoire_id = uuid.UUID(request.repertoire_id)

            start_line_id = (
                uuid.UUID(request.start_line_id)
                if request.start_line_id
                else None
            )
        except ValueError:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                'Invalid UUID',
            )

        async with AsyncSessionFactory() as session, session.begin():
            repertoire = await session.scalar(
                select(Repertoire)
                .where(
                    Repertoire.id == repertoire_id,
                    Repertoire.user_id == user_id,
                )
                .with_for_update(),
            )

            if repertoire is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    'Repertoire not found',
                )

            lines = list(
                await session.scalars(
                    select(Line)
                    .where(
                        Line.repertoire_id == repertoire_id,
                    )
                    .with_for_update(),
                ),
            )

            lines_by_id = {
                line.id: line
                for line in lines
            }

            children_by_parent: dict[
                uuid.UUID,
                list[Line],
            ] = defaultdict(list)

            for line in lines:
                if line.parent_id is not None:
                    children_by_parent[line.parent_id].append(line)

            if start_line_id is None:
                start_line = next(
                    (
                        line
                        for line in lines
                        if line.parent_id is None
                    ),
                    None,
                )
            else:
                start_line = lines_by_id.get(start_line_id)

            if start_line is None:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    'Start line not found',
                )

            self._synchronize_tree(
                start_line,
                children_by_parent,
            )

            response_lines = self._build_training_tree(
                start_line,
                children_by_parent,
            )

            return repertoire_pb2.GetTrainingTreeResponse( # type: ignore
                repertoire_revision=repertoire.revision,
                lines=response_lines,
            )

    @staticmethod
    def _synchronize_tree(
            start_line: Line,
            children_by_parent: dict[uuid.UUID, list[Line]],
            ) -> None:

        children = children_by_parent.get(
            start_line.id,
            [],
        )

        for child in children:
            if (
                child.parent_analytic_version
                != start_line.analytic_version
            ):
                child.analytic_version += 1
                child.parent_analytic_version = (
                    start_line.analytic_version
                )

            RepertoireGrpcService._synchronize_tree(
                child,
                children_by_parent,
            )

    @staticmethod
    def _build_training_tree(
            start_line: Line,
            children_by_parent: dict[uuid.UUID, list[Line]],
            ) -> list[Any]:

        result: list[Any] = []

        def visit(line: Line,
                  is_root: bool
                  ) -> None:

            result.append(
                repertoire_pb2.TrainingLine( # type: ignore
                    id=str(line.id),
                    parent_id=(
                        ''
                        if is_root
                        else str(line.parent_id)
                    ),
                    tag=line.tag or '',
                    moves=line.moves,
                    analytic_version=line.analytic_version,
                ),
            )

            for child in children_by_parent.get(line.id, []):
                visit(
                    child,
                    is_root=False,
                )

        visit(
            start_line,
            is_root=True,
        )

        return result
