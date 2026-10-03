from uuid import uuid4

import pytest

from grpc_client.client import RepertoireGrpcClient
from grpc_client.models import TrainingTree
from grpc_gen.repertoire.v1 import repertoire_pb2


class FakeStub:
    def __init__(self):
        self.training_tree_request = None
        self.training_tree_timeout = None
        self.revision_request = None
        self.revision_timeout = None

        self.training_tree_response = None
        self.revision_response = None

    async def GetTrainingTree(
        self,
        request,
        timeout,
    ):
        self.training_tree_request = request
        self.training_tree_timeout = timeout
        return self.training_tree_response

    async def GetRepertoireRevision(
        self,
        request,
        timeout,
    ):
        self.revision_request = request
        self.revision_timeout = timeout
        return self.revision_response


class FakeChannel:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


@pytest.fixture
def client(monkeypatch):
    client = object.__new__(RepertoireGrpcClient)

    client._stub = FakeStub()
    client._channel = FakeChannel()
    client._timeout = 2.5

    return client


@pytest.mark.asyncio
async def test_get_training_tree_maps_response(client):
    user_id = uuid4()
    repertoire_id = uuid4()
    start_line_id = uuid4()

    line_id = uuid4()
    parent_id = uuid4()

    client._stub.training_tree_response = (
        repertoire_pb2.GetTrainingTreeResponse(
            repertoire_revision=7,
            lines=[
                repertoire_pb2.TrainingLine(
                    id=str(line_id),
                    parent_id=str(parent_id),
                    tag='main',
                    moves=['e2e4', 'e7e5'],
                    analytic_version=3,
                ),
                repertoire_pb2.TrainingLine(
                    id=str(uuid4()),
                    parent_id='',
                    tag='',
                    moves=['d2d4'],
                    analytic_version=1,
                ),
            ],
        )
    )

    result = await client.get_training_tree(
        user_id,
        repertoire_id,
        start_line_id,
    )

    assert isinstance(result, TrainingTree)
    assert result.repertoire_revision == 7
    assert len(result.lines) == 2

    assert result.lines[0].id == line_id
    assert result.lines[0].parent_id == parent_id
    assert result.lines[0].tag == 'main'
    assert result.lines[0].moves == [
        'e2e4',
        'e7e5',
    ]
    assert result.lines[0].analytic_version == 3

    assert result.lines[1].parent_id is None
    assert result.lines[1].tag is None

    request = client._stub.training_tree_request

    assert request.user_id == str(user_id)
    assert request.repertoire_id == str(repertoire_id)
    assert request.start_line_id == str(start_line_id)
    assert client._stub.training_tree_timeout == 2.5


@pytest.mark.asyncio
async def test_get_training_tree_without_start_line(client):
    user_id = uuid4()
    repertoire_id = uuid4()

    client._stub.training_tree_response = (
        repertoire_pb2.GetTrainingTreeResponse(
            repertoire_revision=1,
        )
    )

    result = await client.get_training_tree(
        user_id,
        repertoire_id,
        None,
    )

    assert result.repertoire_revision == 1
    assert result.lines == []

    assert (
        client._stub.training_tree_request.start_line_id
        == ''
    )


@pytest.mark.asyncio
async def test_get_repertoire_revision(client):
    user_id = uuid4()
    repertoire_id = uuid4()

    client._stub.revision_response = (
        repertoire_pb2.GetRepertoireRevisionResponse(
            repertoire_revision=42,
        )
    )

    result = await client.get_repertoire_revision(
        user_id,
        repertoire_id,
    )

    assert result == 42

    request = client._stub.revision_request

    assert request.user_id == str(user_id)
    assert request.repertoire_id == str(repertoire_id)
    assert client._stub.revision_timeout == 2.5


@pytest.mark.asyncio
async def test_close(client):
    assert not client._channel.closed

    await client.close()

    assert client._channel.closed
