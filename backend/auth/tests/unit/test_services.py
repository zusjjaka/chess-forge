from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from exceptions import UserAlreadyExistError
from services.auth import AuthService


@pytest.fixture
def session():
    session = AsyncMock()
    return session


@pytest.fixture
def service(session):
    return AuthService(session)


@pytest.mark.asyncio
async def test_register_creates_user(service):
    user = Mock()
    user.email = 'test@example.com'

    service.users.get_by_email = AsyncMock(return_value=None)
    service.users.create = AsyncMock(return_value=user)

    with patch(
        'services.auth.hash_password',
        return_value='hashed-password',
    ) as hash_password:
        result = await service.register(
            email='test@example.com',
            password='password123',
        )

    assert result is user

    service.users.get_by_email.assert_awaited_once_with('test@example.com')

    hash_password.assert_called_once_with('password123')

    service.users.create.assert_awaited_once_with(
        email='test@example.com',
        password_hash='hashed-password',
    )

    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_rejects_existing_user(service):
    existing_user = Mock()

    service.users.get_by_email = AsyncMock(return_value=existing_user)

    with pytest.raises(UserAlreadyExistError):
        await service.register(
            email='test@example.com',
            password='password123',
        )

    service.users.create.assert_not_called()
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(service):
    service.users.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            email='test@example.com',
            password='password123',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid credentials'


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(service):
    user = Mock()
    user.password_hash = 'hashed-password'

    service.users.get_by_email = AsyncMock(return_value=user)

    with (
        patch(
            'services.auth.verify_password',
            return_value=False,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.login(
            email='test@example.com',
            password='wrong-password',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid credentials'


@pytest.mark.asyncio
async def test_login_creates_tokens(service):
    user = Mock()
    user.id = uuid4()
    user.password_hash = 'hashed-password'

    service.users.get_by_email = AsyncMock(return_value=user)
    service.refresh_tokens.create = AsyncMock()

    with (
        patch(
            'services.auth.verify_password',
            return_value=True,
        ),
        patch(
            'services.auth.create_access_token',
            return_value='access-token',
        ),
        patch(
            'services.auth.generate_refresh_token',
            return_value='refresh-token',
        ),
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'hash',
        ),
    ):
        access_token, refresh_token = await service.login(
            email='test@example.com',
            password='password123',
            ip_addr='127.0.0.1',
            user_agent='pytest',
        )

    assert access_token == 'access-token'
    assert refresh_token == 'refresh-token'

    service.refresh_tokens.create.assert_awaited_once()
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_rejects_unknown_token(service):
    service.refresh_tokens.get_by_hash = AsyncMock(return_value=None)

    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'hash',
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.refresh(
            refresh_token='invalid-token',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid refresh token'


@pytest.mark.asyncio
async def test_refresh_rejects_reused_token(service):
    stored_token = Mock()
    stored_token.is_active = False
    stored_token.family_id = uuid4()

    service.refresh_tokens.get_by_hash = AsyncMock(return_value=stored_token)
    service.refresh_tokens.revoke_family = AsyncMock()

    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'hash',
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.refresh(
            refresh_token='refresh-token',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Refresh token reuse detected'

    service.refresh_tokens.revoke_family.assert_awaited_once_with(
        stored_token.family_id
    )
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token(service):
    stored_token = Mock()
    stored_token.is_active = True
    stored_token.expires_at = datetime.now(UTC) - timedelta(minutes=1)

    service.refresh_tokens.get_by_hash = AsyncMock(return_value=stored_token)
    service.refresh_tokens.revoke = AsyncMock()

    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'hash',
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.refresh(
            refresh_token='refresh-token',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Refresh token expired'

    service.refresh_tokens.revoke.assert_awaited_once_with(stored_token)
    service.session.commit.assert_awaited_once()
