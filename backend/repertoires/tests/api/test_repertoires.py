import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import (
    get_current_user_id,
    get_repertoire_service,
)
from main import app
from models.repertoire import (
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
    now = datetime.now(timezone.utc)

    return Repertoire(
        id=uuid.uuid4(),
        user_id=user_id,
        name='Italian Game',
        description='King pawn opening',
        side=RepertoireSide.WHITE,
        revision=1,
        analytic_version=1,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_repertoires(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        ) -> None:
    service = AsyncMock()

    service.list.return_value = (
        [repertoire],
        1,
        1,
    )

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                '/api/v1/repertoires',
            )

        assert response.status_code == 200

        body = response.json()

        assert body['page'] == 1
        assert body['pages'] == 1
        assert len(body['items']) == 1
        assert body['items'][0]['id'] == str(repertoire.id)
        assert body['items'][0]['revision'] == 1
        assert body['items'][0]['analytic_version'] == 1

        service.list.assert_awaited_once_with(
            user_id,
            1,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_repertoires_accepts_page(
        user_id: uuid.UUID,
        ) -> None:
    service = AsyncMock()

    service.list.return_value = (
        [],
        2,
        3,
    )

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                '/api/v1/repertoires?page=2',
            )

        assert response.status_code == 200

        service.list.assert_awaited_once_with(
            user_id,
            2,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_repertoires_rejects_invalid_page(
        user_id: uuid.UUID,
        ) -> None:
    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                '/api/v1/repertoires?page=0',
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_repertoire(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        ) -> None:
    service = AsyncMock()
    service.create.return_value = repertoire

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.post(
                '/api/v1/repertoires',
                json={
                    'name': 'Italian Game',
                    'description': 'King pawn opening',
                    'side': 'white',
                },
            )

        assert response.status_code == 201

        body = response.json()

        assert body['id'] == str(repertoire.id)
        assert body['name'] == 'Italian Game'
        assert body['description'] == 'King pawn opening'
        assert body['side'] == 'white'
        assert body['revision'] == 1
        assert body['analytic_version'] == 1

        service.create.assert_awaited_once()

        args = service.create.await_args.args

        assert args[0] == user_id
        assert args[1].name == 'Italian Game'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_repertoire_rejects_invalid_body(
        user_id: uuid.UUID,
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
                '/api/v1/repertoires',
                json={
                    'name': '',
                    'side': 'white',
                },
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repertoire(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        ) -> None:
    service = AsyncMock()
    service.get.return_value = repertoire

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                f'/api/v1/repertoires/{repertoire.id}',
            )

        assert response.status_code == 200

        body = response.json()

        assert body['id'] == str(repertoire.id)
        assert body['user_id'] == str(user_id)
        assert body['revision'] == 1
        assert body['analytic_version'] == 1

        service.get.assert_awaited_once_with(
            repertoire.id,
            user_id,
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_repertoire_rejects_invalid_uuid(
        user_id: uuid.UUID,
        ) -> None:
    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                '/api/v1/repertoires/not-a-uuid',
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_repertoire(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        ) -> None:
    service = AsyncMock()
    service.update.return_value = repertoire

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.patch(
                f'/api/v1/repertoires/{repertoire.id}',
                json={
                    'name': 'Updated repertoire',
                },
            )

        assert response.status_code == 200

        service.update.assert_awaited_once()

        args = service.update.await_args.args

        assert args[0] == repertoire.id
        assert args[1] == user_id
        assert args[2].name == 'Updated repertoire'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_repertoire(
        user_id: uuid.UUID,
        repertoire: Repertoire,
        ) -> None:
    service = AsyncMock()

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: user_id

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.delete(
                f'/api/v1/repertoires/{repertoire.id}',
            )

        assert response.status_code == 204

        service.delete.assert_awaited_once_with(
            repertoire.id,
            user_id,
        )
    finally:
        app.dependency_overrides.clear()
