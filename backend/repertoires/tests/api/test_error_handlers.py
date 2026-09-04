import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from api.dependencies import (
    get_current_user_id,
    get_line_service,
    get_repertoire_service,
)
from exceptions import (
    DatabaseCheckConstraintError,
    DatabaseConnectionError,
    DatabaseError,
    InvalidLineRelationshipError,
    LineNotFoundError,
    RepertoireNotFoundError,
    RootLineAlreadyExistsError,
    RootLineDeletionError,
)
from main import app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        'exception',
        'status_code',
        'detail',
    ),
    [
        (
            RepertoireNotFoundError(),
            404,
            'Repertoire not found',
        ),
        (
            LineNotFoundError(),
            404,
            'Line not found',
        ),
        (
            RootLineDeletionError(),
            400,
            'Root line cannot be deleted',
        ),
    ],
)
async def test_api_exception_handler(
        exception: Exception,
        status_code: int,
        detail: str,
        ) -> None:
    async def raise_exception(
            *args: object,
            **kwargs: object,
            ) -> object:
        raise exception

    service = AsyncMock()
    service.get.side_effect = raise_exception

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: uuid.uuid4()

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                f'/api/v1/repertoires/{uuid.uuid4()}',
            )

        assert response.status_code == status_code
        assert response.json() == {
            'detail': detail,
        }
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_database_error_handler() -> None:
    service = AsyncMock()
    service.get.side_effect = DatabaseError()

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: uuid.uuid4()

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                f'/api/v1/repertoires/{uuid.uuid4()}',
            )

        assert response.status_code == 500
        assert response.json() == {
            'detail': 'Internal server error',
        }
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_database_connection_error_handler() -> None:
    service = AsyncMock()
    service.get.side_effect = DatabaseConnectionError()

    app.dependency_overrides[
        get_current_user_id
    ] = lambda: uuid.uuid4()

    app.dependency_overrides[
        get_repertoire_service
    ] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            response = await client.get(
                f'/api/v1/repertoires/{uuid.uuid4()}',
            )

        assert response.status_code == 503
        assert response.json() == {
            'detail': 'Database unavailable',
        }
    finally:
        app.dependency_overrides.clear()
