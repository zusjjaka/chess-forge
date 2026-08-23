import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from api.dependencies import get_current_user
from exceptions import InvalidAccessTokenError
from models.user import User


@pytest.mark.asyncio
async def test_get_current_user_returns_user() -> None:
    user_id = uuid.uuid4()

    user = User(
        id=user_id,
        email='user@example.com',
        password_hash='password-hash',
    )

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )

    session = AsyncMock()

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': str(user_id)},
        ),
        patch(
            'api.dependencies.UserRepository.get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ),
    ):
        result = await get_current_user(credentials, session)

    assert result is user


@pytest.mark.asyncio
async def test_get_current_user_invalid_token() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='invalid-token',
    )

    session = AsyncMock()

    with (
        patch(
            'api.dependencies.decode_access_token',
            side_effect=ValueError,
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_current_user(credentials, session)


@pytest.mark.asyncio
async def test_get_current_user_missing_sub() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )

    session = AsyncMock()

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={},
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_current_user(credentials, session)


@pytest.mark.asyncio
async def test_get_current_user_invalid_user_id() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )

    session = AsyncMock()

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': 'not-a-uuid'},
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_current_user(credentials, session)


@pytest.mark.asyncio
async def test_get_current_user_user_not_found() -> None:
    user_id = uuid.uuid4()

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )

    session = AsyncMock()

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': str(user_id)},
        ),
        patch(
            'api.dependencies.UserRepository.get_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_current_user(credentials, session)
