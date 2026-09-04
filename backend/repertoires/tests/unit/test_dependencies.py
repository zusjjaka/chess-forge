import uuid
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi.security import HTTPAuthorizationCredentials

from api.dependencies import (
    get_current_user_id,
    get_line_service,
    get_repertoire_service,
)
from exceptions import InvalidAccessTokenError
from services.line import LineService
from services.repertoire import RepertoireService


@pytest.mark.asyncio
async def test_get_current_user_id_returns_uuid(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    user_id = uuid.uuid4()

    monkeypatch.setattr(
        'api.dependencies.decode_access_token',
        lambda token: {'sub': str(user_id)},
    )

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='access-token',
    )

    result = get_current_user_id(credentials)

    assert result == user_id


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_invalid_uuid(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    monkeypatch.setattr(
        'api.dependencies.decode_access_token',
        lambda token: {'sub': 'not-a-uuid'},
    )

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='access-token',
    )

    with pytest.raises(InvalidAccessTokenError):
        get_current_user_id(credentials)


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_missing_sub(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    monkeypatch.setattr(
        'api.dependencies.decode_access_token',
        lambda token: {},
    )

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='access-token',
    )

    with pytest.raises(InvalidAccessTokenError):
        get_current_user_id(credentials)


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_invalid_token(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    def raise_invalid_token(token: str) -> dict[str, object]:
        raise jwt.InvalidTokenError('invalid token')

    monkeypatch.setattr(
        'api.dependencies.decode_access_token',
        raise_invalid_token,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='access-token',
    )

    with pytest.raises(InvalidAccessTokenError):
        get_current_user_id(credentials)


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_value_error(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    def raise_value_error(token: str) -> dict[str, object]:
        raise ValueError('invalid value')

    monkeypatch.setattr(
        'api.dependencies.decode_access_token',
        raise_value_error,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='access-token',
    )

    with pytest.raises(InvalidAccessTokenError):
        get_current_user_id(credentials)


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_key_error(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    def raise_key_error(token: str) -> dict[str, object]:
        raise KeyError('sub')

    monkeypatch.setattr(
        'api.dependencies.decode_access_token',
        raise_key_error,
    )

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='access-token',
    )

    with pytest.raises(InvalidAccessTokenError):
        get_current_user_id(credentials)


@pytest.mark.asyncio
async def test_get_repertoire_service_returns_service() -> None:
    session = MagicMock()

    service = get_repertoire_service(session)

    assert isinstance(service, RepertoireService)
    assert service.session is session


@pytest.mark.asyncio
async def test_get_line_service_returns_service() -> None:
    session = MagicMock()

    service = get_line_service(session)

    assert isinstance(service, LineService)
    assert service.session is session
