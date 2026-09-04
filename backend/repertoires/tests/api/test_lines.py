import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import (
    get_current_user_id,
    get_line_service,
)
from main import app
from models.repertoire import (
    Line,
    Repertoire,
    RepertoireSide,
)


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def repertoire(
        user_id: uuid.UUID,
        ) -> Repertoire:
    return Repertoire(
        id=uuid.uuid4(),
        user_id=user_id,
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
        tag=None,
        moves=['e2e4'],
    )


@pytest.mark.asyncio
async def test_get_lines(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service = AsyncMock()

    service.get_tree_response.return_value = {
        'id': root.id,
        'tag': None,
        'moves': ['e2e4'],
        'children': [],
    }

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_line_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                f'/api/v1/repertoires/{repertoire.id}/lines',
            )

        assert response.status_code == 200

        body = response.json()

        assert body['id'] == str(root.id)
        assert body['moves'] == ['e2e4']
        assert body['children'] == []

        service.get_tree_response.assert_awaited_once_with(
            repertoire.id,
            user_id,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_line(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service = AsyncMock()

    service.get_line_response.return_value = {
        'id': root.id,
        'tag': 'Root',
        'moves': ['e2e4'],
        'children': [],
    }

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_line_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                f'/api/v1/repertoires/{repertoire.id}/lines/{root.id}',
            )

        assert response.status_code == 200

        body = response.json()

        assert body['id'] == str(root.id)
        assert body['tag'] == 'Root'

        service.get_line_response.assert_awaited_once_with(
            repertoire.id,
            root.id,
            user_id,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_line(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service = AsyncMock()

    child = Line(
        id=uuid.uuid4(),
        repertoire_id=repertoire.id,
        parent_id=root.id,
        tag='Main line',
        moves=['e7e5', 'g1f3'],
    )

    service.create_child.return_value = child

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_line_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.post(
                f'/api/v1/repertoires/{repertoire.id}/lines/{root.id}',
                json={
                    'tag': 'Main line',
                    'moves': ['e7e5', 'g1f3'],
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body['id'] == str(child.id)
        assert body['tag'] == 'Main line'
        assert body['moves'] == ['e7e5', 'g1f3']

        service.create_child.assert_awaited_once()

        args = service.create_child.await_args.args

        assert args[0] == repertoire.id
        assert args[1] == root.id
        assert args[2] == user_id
        assert args[3].moves == ['e7e5', 'g1f3']
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_line_rejects_empty_moves(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.post(
                f'/api/v1/repertoires/{repertoire.id}/lines/{root.id}',
                json={
                    'moves': [],
                },
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_line(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service = AsyncMock()
    service.update.return_value = root

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_line_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.patch(
                f'/api/v1/repertoires/{repertoire.id}/lines/{root.id}',
                json={
                    'tag': 'Updated',
                },
            )

        assert response.status_code == 200

        service.update.assert_awaited_once()

        args = service.update.await_args.args

        assert args[0] == repertoire.id
        assert args[1] == root.id
        assert args[2] == user_id
        assert args[3].tag == 'Updated'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_line(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        root: Line,
        ) -> None:
    service = AsyncMock()

    child_id = uuid.uuid4()

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_line_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.delete(
                f'/api/v1/repertoires/{repertoire.id}/lines/{child_id}',
            )

        assert response.status_code == 204

        service.delete.assert_awaited_once_with(
            repertoire.id,
            child_id,
            user_id,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_replace_tree(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        ) -> None:
    service = AsyncMock()

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_line_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.put(
                f'/api/v1/repertoires/{repertoire.id}/lines',
                json={
                    'version': 1,
                    'tree': {
                        'tag': 'Root',
                        'moves': ['e2e4'],
                        'children': [],
                    },
                },
            )

        assert response.status_code == 204

        service.replace_tree.assert_awaited_once()

        args = service.replace_tree.await_args.args

        assert args[0] == repertoire.id
        assert args[1] == user_id
        assert args[2].version == 1
        assert args[2].tree.moves == ['e2e4']
    finally:
        app.dependency_overrides.clear()
