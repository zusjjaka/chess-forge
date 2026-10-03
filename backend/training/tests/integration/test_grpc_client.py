from uuid import uuid4

import grpc
import pytest
from grpc.aio import server

from grpc_client.client import RepertoireGrpcClient
from grpc_gen.repertoire.v1 import (
    repertoire_pb2,
    repertoire_pb2_grpc,
)


class FakeRepertoireServicer(
    repertoire_pb2_grpc.RepertoireServiceServicer,
):
    def __init__(self):
        self.tree_requests = []
        self.revision_requests = []

    async def GetTrainingTree(
        self,
        request,
        context,
    ):
        self.tree_requests.append(request)

        return repertoire_pb2.GetTrainingTreeResponse(
            repertoire_revision=7,
            lines=[
                repertoire_pb2.TrainingLine(
                    id=str(uuid4()),
                    parent_id='',
                    tag='root',
                    moves=['e2e4'],
                    analytic_version=3,
                ),
            ],
        )

    async def GetRepertoireRevision(
        self,
        request,
        context,
    ):
        self.revision_requests.append(request)

        return repertoire_pb2.GetRepertoireRevisionResponse(
            repertoire_revision=9,
        )


@pytest.mark.asyncio
async def test_repertoire_grpc_client_with_real_grpc_server(
    monkeypatch,
):
    grpc_server = server()
    servicer = FakeRepertoireServicer()

    repertoire_pb2_grpc.add_RepertoireServiceServicer_to_server(
        servicer,
        grpc_server,
    )

    port = grpc_server.add_insecure_port(
        '127.0.0.1:0'
    )

    await grpc_server.start()

    client = object.__new__(RepertoireGrpcClient)

    channel = grpc.aio.insecure_channel(
        f'127.0.0.1:{port}'
    )

    client._channel = channel
    client._stub = (
        repertoire_pb2_grpc.RepertoireServiceStub(channel)
    )
    client._timeout = 2.0

    user_id = uuid4()
    repertoire_id = uuid4()
    start_line_id = uuid4()

    try:
        tree = await client.get_training_tree(
            user_id,
            repertoire_id,
            start_line_id,
        )

        assert tree.repertoire_revision == 7
        assert len(tree.lines) == 1
        assert tree.lines[0].tag == 'root'
        assert tree.lines[0].moves == ['e2e4']
        assert tree.lines[0].analytic_version == 3

        assert len(servicer.tree_requests) == 1

        request = servicer.tree_requests[0]

        assert request.user_id == str(user_id)
        assert request.repertoire_id == str(repertoire_id)
        assert request.start_line_id == str(
            start_line_id
        )

        revision = (
            await client.get_repertoire_revision(
                user_id,
                repertoire_id,
            )
        )

        assert revision == 9

        assert len(servicer.revision_requests) == 1

        revision_request = servicer.revision_requests[0]

        assert revision_request.user_id == str(user_id)
        assert (
            revision_request.repertoire_id
            == str(repertoire_id)
        )
    finally:
        await client.close()
        await grpc_server.stop(0)
