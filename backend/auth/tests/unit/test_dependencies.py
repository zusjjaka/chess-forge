from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.dependencies import get_current_user


@pytest.mark.asyncio
async def test_get_current_user():
    user_id = uuid4()
    user = Mock()
    user.id = user_id

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )

    repository = Mock()
    repository.get_by_id = AsyncMock(return_value=user)

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': str(user_id)},
        ),
        patch(
            'api.dependencies.UserRepository',
            return_value=repository,
        ),
    ):
        result = await get_current_user(
            credentials=credentials,
            session=Mock(),
        )

    assert result is user

    repository.get_by_id.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_get_current_user_invalid_uuid():
    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='invalid-token',
    )

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': 'not-a-uuid'},
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_current_user(
            credentials=credentials,
            session=Mock(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid access token'


@pytest.mark.asyncio
async def test_get_current_user_missing_sub():
    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={},
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_current_user(
            credentials=credentials,
            session=Mock(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid access token'


@pytest.mark.asyncio
async def test_get_current_user_not_found():
    user_id = uuid4()

    credentials = HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )

    repository = Mock()
    repository.get_by_id = AsyncMock(return_value=None)

    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': str(user_id)},
        ),
        patch(
            'api.dependencies.UserRepository',
            return_value=repository,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_current_user(
            credentials=credentials,
            session=Mock(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'User not found'
