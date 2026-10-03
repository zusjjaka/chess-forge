import uuid

import grpc
import pytest
import pytest_asyncio
from grpc.aio import AioRpcError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
)

import rpc.service as rpc_service
from grpc_gen.repertoire.v1 import repertoire_pb2
from grpc_gen.repertoire.v1 import repertoire_pb2_grpc
from models.line import Line
from models.repertoire import Repertoire, RepertoireSide
from rpc.service import RepertoireGrpcService


@pytest_asyncio.fixture
async def grpc_stub(
        engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
        ):
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    monkeypatch.setattr(
        rpc_service,
        'AsyncSessionFactory',
        session_factory,
    )

    server = grpc.aio.server()

    repertoire_pb2_grpc.add_RepertoireServiceServicer_to_server(
        RepertoireGrpcService(),
        server,
    )

    port = server.add_insecure_port('127.0.0.1:0')

    await server.start()

    channel = grpc.aio.insecure_channel(
        f'127.0.0.1:{port}',
    )

    stub = repertoire_pb2_grpc.RepertoireServiceStub(channel)

    yield stub

    await channel.close()
    await server.stop(grace=0)


@pytest.mark.asyncio
async def test_get_training_tree(
        session,
        grpc_stub,
        ):
    user_id = uuid.uuid4()
    repertoire_id = uuid.uuid4()
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    grandchild_id = uuid.uuid4()

    repertoire = Repertoire(
        id=repertoire_id,
        user_id=user_id,
        name='Sicilian Defense',
        description='',
        side=RepertoireSide.WHITE,
        revision=7,
    )

    root = Line(
        id=root_id,
        repertoire_id=repertoire_id,
        parent_id=None,
        tag='Sicilian',
        moves=['e2e4'],
        analytic_version=2,
    )

    child = Line(
        id=child_id,
        repertoire_id=repertoire_id,
        parent_id=root_id,
        tag='Najdorf',
        moves=['c7c5', 'g1f3'],
        analytic_version=3,
        parent_analytic_version=2,
    )

    grandchild = Line(
        id=grandchild_id,
        repertoire_id=repertoire_id,
        parent_id=child_id,
        tag=None,
        moves=['d7d6', 'd2d4'],
        analytic_version=1,
        parent_analytic_version=3,
    )

    session.add_all([
        repertoire,
        root,
        child,
        grandchild,
    ])
    await session.commit()

    response = await grpc_stub.GetTrainingTree(
        repertoire_pb2.GetTrainingTreeRequest(
            user_id=str(user_id),
            repertoire_id=str(repertoire_id),
        ),
    )

    assert response.repertoire_revision == 7
    assert len(response.lines) == 3

    root_response = response.lines[0]
    child_response = response.lines[1]
    grandchild_response = response.lines[2]

    assert root_response.id == str(root_id)
    assert root_response.parent_id == ''
    assert root_response.tag == 'Sicilian'
    assert list(root_response.moves) == ['e2e4']
    assert root_response.analytic_version == 2

    assert child_response.id == str(child_id)
    assert child_response.parent_id == str(root_id)
    assert child_response.tag == 'Najdorf'
    assert list(child_response.moves) == ['c7c5', 'g1f3']
    assert child_response.analytic_version == 3

    assert grandchild_response.id == str(grandchild_id)
    assert grandchild_response.parent_id == str(child_id)
    assert grandchild_response.tag == ''
    assert list(grandchild_response.moves) == ['d7d6', 'd2d4']
    assert grandchild_response.analytic_version == 1


@pytest.mark.asyncio
async def test_get_training_tree_from_start_line(
        session,
        grpc_stub,
        ):
    user_id = uuid.uuid4()
    repertoire_id = uuid.uuid4()
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    grandchild_id = uuid.uuid4()

    session.add_all([
        Repertoire(
            id=repertoire_id,
            user_id=user_id,
            name='Opening',
            description='',
            side=RepertoireSide.WHITE,
            revision=3,
        ),
        Line(
            id=root_id,
            repertoire_id=repertoire_id,
            parent_id=None,
            moves=['e2e4'],
        ),
        Line(
            id=child_id,
            repertoire_id=repertoire_id,
            parent_id=root_id,
            moves=['e7e5', 'g1f3'],
        ),
        Line(
            id=grandchild_id,
            repertoire_id=repertoire_id,
            parent_id=child_id,
            moves=['b8c6', 'f1b5'],
        ),
    ])
    await session.commit()

    response = await grpc_stub.GetTrainingTree(
        repertoire_pb2.GetTrainingTreeRequest(
            user_id=str(user_id),
            repertoire_id=str(repertoire_id),
            start_line_id=str(child_id),
        ),
    )

    assert response.repertoire_revision == 3
    assert len(response.lines) == 2

    start_line = response.lines[0]
    grandchild = response.lines[1]

    assert start_line.id == str(child_id)
    assert start_line.parent_id == ''
    assert start_line.moves == ['e7e5', 'g1f3']

    assert grandchild.id == str(grandchild_id)
    assert grandchild.parent_id == str(child_id)


@pytest.mark.asyncio
async def test_get_training_tree_synchronizes_analytic_versions(
        session,
        grpc_stub,
        ):
    user_id = uuid.uuid4()
    repertoire_id = uuid.uuid4()
    root_id = uuid.uuid4()
    child_id = uuid.uuid4()
    grandchild_id = uuid.uuid4()

    session.add_all([
        Repertoire(
            id=repertoire_id,
            user_id=user_id,
            name='Opening',
            description='',
            side=RepertoireSide.WHITE,
            revision=5,
        ),
        Line(
            id=root_id,
            repertoire_id=repertoire_id,
            parent_id=None,
            moves=['e2e4'],
            analytic_version=5,
        ),
        Line(
            id=child_id,
            repertoire_id=repertoire_id,
            parent_id=root_id,
            moves=['e7e5', 'g1f3'],
            analytic_version=2,
            parent_analytic_version=3,
        ),
        Line(
            id=grandchild_id,
            repertoire_id=repertoire_id,
            parent_id=child_id,
            moves=['b8c6', 'f1b5'],
            analytic_version=4,
            parent_analytic_version=2,
        ),
    ])
    await session.commit()

    await grpc_stub.GetTrainingTree(
        repertoire_pb2.GetTrainingTreeRequest(
            user_id=str(user_id),
            repertoire_id=str(repertoire_id),
        ),
    )

    session.expire_all()

    lines = (
        await session.scalars(
            select(Line)
            .where(
                Line.id.in_([
                    child_id,
                    grandchild_id,
                ]),
            ),
        )
    ).all()

    lines_by_id = {
        line.id: line
        for line in lines
    }

    child = lines_by_id[child_id]
    grandchild = lines_by_id[grandchild_id]

    assert child.analytic_version == 3
    assert child.parent_analytic_version == 5

    assert grandchild.analytic_version == 5
    assert grandchild.parent_analytic_version == 3


@pytest.mark.asyncio
async def test_get_training_tree_invalid_user_uuid(
        grpc_stub,
        ):
    with pytest.raises(AioRpcError) as error:
        await grpc_stub.GetTrainingTree(
            repertoire_pb2.GetTrainingTreeRequest(
                user_id='invalid',
                repertoire_id=str(uuid.uuid4()),
            ),
        )

    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert error.value.details() == 'Invalid UUID'


@pytest.mark.asyncio
async def test_get_training_tree_invalid_repertoire_uuid(
        grpc_stub,
        ):
    with pytest.raises(AioRpcError) as error:
        await grpc_stub.GetTrainingTree(
            repertoire_pb2.GetTrainingTreeRequest(
                user_id=str(uuid.uuid4()),
                repertoire_id='invalid',
            ),
        )

    assert error.value.code() == grpc.StatusCode.INVALID_ARGUMENT
    assert error.value.details() == 'Invalid UUID'


@pytest.mark.asyncio
async def test_get_training_tree_repertoire_not_found(
        grpc_stub,
        ):
    with pytest.raises(AioRpcError) as error:
        await grpc_stub.GetTrainingTree(
            repertoire_pb2.GetTrainingTreeRequest(
                user_id=str(uuid.uuid4()),
                repertoire_id=str(uuid.uuid4()),
            ),
        )

    assert error.value.code() == grpc.StatusCode.NOT_FOUND
    assert error.value.details() == 'Repertoire not found'


@pytest.mark.asyncio
async def test_get_training_tree_user_not_owner(
        session,
        grpc_stub,
        ):
    owner_id = uuid.uuid4()
    another_user_id = uuid.uuid4()
    repertoire_id = uuid.uuid4()

    session.add(
        Repertoire(
            id=repertoire_id,
            user_id=owner_id,
            name='Private repertoire',
            description='',
            side=RepertoireSide.WHITE,
            revision=1,
        ),
    )
    await session.commit()

    with pytest.raises(AioRpcError) as error:
        await grpc_stub.GetTrainingTree(
            repertoire_pb2.GetTrainingTreeRequest(
                user_id=str(another_user_id),
                repertoire_id=str(repertoire_id),
            ),
        )

    assert error.value.code() == grpc.StatusCode.NOT_FOUND
    assert error.value.details() == 'Repertoire not found'


@pytest.mark.asyncio
async def test_get_training_tree_start_line_not_found(
        session,
        grpc_stub,
        ):
    user_id = uuid.uuid4()
    repertoire_id = uuid.uuid4()

    session.add(
        Repertoire(
            id=repertoire_id,
            user_id=user_id,
            name='Opening',
            description='',
            side=RepertoireSide.WHITE,
            revision=1,
        ),
    )
    await session.commit()

    with pytest.raises(AioRpcError) as error:
        await grpc_stub.GetTrainingTree(
            repertoire_pb2.GetTrainingTreeRequest(
                user_id=str(user_id),
                repertoire_id=str(repertoire_id),
                start_line_id=str(uuid.uuid4()),
            ),
        )

    assert error.value.code() == grpc.StatusCode.NOT_FOUND
    assert error.value.details() == 'Start line not found'
