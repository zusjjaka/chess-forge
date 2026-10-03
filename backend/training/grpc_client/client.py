from uuid import UUID

import grpc

from core.config import get_settings
from grpc_client.models import (
    TrainingLine,
    TrainingTree,
)
from grpc_gen.repertoire.v1 import repertoire_pb2, repertoire_pb2_grpc


class RepertoireGrpcClient:
    def __init__(self) -> None:
        settings = get_settings()

        self._channel = grpc.aio.insecure_channel(
            f'{settings.repertoire_service.host}:'
            f'{settings.repertoire_service.port}',
        )

        self._timeout = settings.repertoire_service.timeout

        self._stub = (
            repertoire_pb2_grpc.RepertoireServiceStub(
                self._channel,
            )
        )

    async def get_training_tree(
            self,
            user_id: UUID,
            repertoire_id: UUID,
            start_line_id: UUID | None,
            ) -> TrainingTree:

        response = await self._stub.GetTrainingTree(
            repertoire_pb2.GetTrainingTreeRequest( # type: ignore
                user_id=str(user_id),
                repertoire_id=str(repertoire_id),
                start_line_id=(
                    str(start_line_id)
                    if start_line_id is not None
                    else ''
                ),
            ),
            timeout=self._timeout,
        )

        lines = [
            TrainingLine(
                id=UUID(line.id),
                parent_id=(
                    UUID(line.parent_id)
                    if line.parent_id
                    else None
                ),
                tag=line.tag or None,
                moves=list(line.moves),
                analytic_version=line.analytic_version,
            )
            for line in response.lines
        ]

        return TrainingTree(
            repertoire_revision=response.repertoire_revision,
            lines=lines,
        )

    async def get_repertoire_revision(
            self,
            user_id: UUID,
            repertoire_id: UUID,
            ) -> int:

        response = await self._stub.GetRepertoireRevision(
            repertoire_pb2.GetRepertoireRevisionRequest( # type: ignore
                user_id=str(user_id),
                repertoire_id=str(repertoire_id),
            ),
            timeout=self._timeout,
        )

        repertoire_revision: int = response.repertoire_revision

        return repertoire_revision

    async def close(self) -> None:
        await self._channel.close()
