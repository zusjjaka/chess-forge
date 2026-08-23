from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from exceptions import UserAlreadyExistError
from models.refresh_token import RefreshToken
from models.user import User
from services.auth import AuthService


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user() -> User:
    return User(
        id=uuid4(),
        email='user@example.com',
        password_hash='hashed-password',
    )


@pytest.fixture
def service(session: AsyncMock) -> AuthService:
    return AuthService(session)


@pytest.mark.asyncio
async def test_register_creates_user(
    service: AuthService,
    user: User,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            service.users,
            'create',
            new_callable=AsyncMock,
            return_value=user,
        ) as create_user,
        patch(
            'services.auth.hash_password',
            return_value='hashed-password',
        ),
    ):
        result = await service.register(
            email='user@example.com',
            password='password123',
        )

    assert result is user

    create_user.assert_awaited_once_with(
        email='user@example.com',
        password_hash='hashed-password',
    )
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_rejects_existing_user(
    service: AuthService,
    user: User,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch.object(
            service.users,
            'create',
            new_callable=AsyncMock,
        ) as create_user,
        pytest.raises(UserAlreadyExistError),
    ):
        await service.register(
            email='user@example.com',
            password='password123',
        )

    create_user.assert_not_awaited()
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_returns_access_and_refresh_tokens(
    service: AuthService,
    user: User,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=user,
        ),
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
            return_value=b'token-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'create',
            new_callable=AsyncMock,
        ) as create_token,
    ):
        access_token, refresh_token = await service.login(
            email='user@example.com',
            password='password123',
            ip_addr='127.0.0.1',
            user_agent='pytest',
        )

    assert access_token == 'access-token'
    assert refresh_token == 'refresh-token'

    create_token.assert_awaited_once()

    call_kwargs = create_token.await_args.kwargs

    assert call_kwargs['user_id'] == user.id
    assert call_kwargs['token_hash'] == b'token-hash'
    assert call_kwargs['ip_addr'] == '127.0.0.1'
    assert call_kwargs['user_agent'] == 'pytest'

    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(
    service: AuthService,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.login(
            email='unknown@example.com',
            password='password123',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid credentials'
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(
    service: AuthService,
    user: User,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            'services.auth.verify_password',
            return_value=False,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.login(
            email='user@example.com',
            password='wrong-password',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid credentials'
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_rotates_refresh_token(
    service: AuthService,
) -> None:
    user_id = uuid4()
    family_id = uuid4()
    old_token_id = uuid4()
    new_token_id = uuid4()

    stored_token = RefreshToken(
        id=old_token_id,
        user_id=user_id,
        hashed_refresh_token=b'old-hash',
        expires_at=datetime.now(UTC) + timedelta(days=1),
        family_id=family_id,
        is_active=True,
    )

    new_token = RefreshToken(
        id=new_token_id,
        user_id=user_id,
        hashed_refresh_token=b'new-hash',
        expires_at=datetime.now(UTC) + timedelta(days=1),
        family_id=family_id,
        is_active=True,
    )

    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'old-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=stored_token,
        ),
        patch(
            'services.auth.generate_refresh_token',
            return_value='new-refresh-token',
        ),
        patch.object(
            service.refresh_tokens,
            'create',
            new_callable=AsyncMock,
            return_value=new_token,
        ),
        patch(
            'services.auth.create_access_token',
            return_value='new-access-token',
        ),
        patch.object(
            service.refresh_tokens,
            'revoke',
            new_callable=AsyncMock,
        ) as revoke,
    ):
        access_token, refresh_token = await service.refresh(
            refresh_token='old-refresh-token',
            ip_addr='127.0.0.1',
            user_agent='pytest',
        )

    assert access_token == 'new-access-token'
    assert refresh_token == 'new-refresh-token'

    revoke.assert_awaited_once_with(
        stored_token,
        replaced_by=new_token.id,
    )
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_rejects_unknown_token(
    service: AuthService,
) -> None:
    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'unknown-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.refresh(
            refresh_token='unknown-token',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Invalid refresh token'


@pytest.mark.asyncio
async def test_refresh_detects_token_reuse(
    service: AuthService,
) -> None:
    stored_token = RefreshToken(
        id=uuid4(),
        user_id=uuid4(),
        hashed_refresh_token=b'token-hash',
        expires_at=datetime.now(UTC) + timedelta(days=1),
        family_id=uuid4(),
        is_active=False,
    )

    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'token-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=stored_token,
        ),
        patch.object(
            service.refresh_tokens,
            'revoke_family',
            new_callable=AsyncMock,
        ) as revoke_family,
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.refresh(
            refresh_token='reused-token',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Refresh token reuse detected'
    revoke_family.assert_awaited_once_with(stored_token.family_id)
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token(
    service: AuthService,
) -> None:
    stored_token = RefreshToken(
        id=uuid4(),
        user_id=uuid4(),
        hashed_refresh_token=b'token-hash',
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        family_id=uuid4(),
        is_active=True,
    )

    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'token-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=stored_token,
        ),
        patch.object(
            service.refresh_tokens,
            'revoke',
            new_callable=AsyncMock,
        ) as revoke,
        pytest.raises(HTTPException) as exc_info,
    ):
        await service.refresh(
            refresh_token='expired-token',
            ip_addr=None,
            user_agent=None,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == 'Refresh token expired'
    revoke.assert_awaited_once_with(stored_token)
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_hashes_password(
    service: AuthService,
    user: User,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            'services.auth.hash_password',
            return_value='hashed-password',
        ) as hash_password,
        patch.object(
            service.users,
            'create',
            new_callable=AsyncMock,
            return_value=user,
        ) as create_user,
    ):
        await service.register(
            email='user@example.com',
            password='password123',
        )

    hash_password.assert_called_once_with('password123')

    create_user.assert_awaited_once_with(
        email='user@example.com',
        password_hash='hashed-password',
    )


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(
    service: AuthService,
) -> None:
    token = RefreshToken(
        id=uuid4(),
        user_id=uuid4(),
        hashed_refresh_token=b'token-hash',
        expires_at=datetime.now(UTC) + timedelta(days=1),
        family_id=uuid4(),
        is_active=True,
    )

    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'token-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=token,
        ),
        patch.object(
            service.refresh_tokens,
            'revoke',
            new_callable=AsyncMock,
        ) as revoke,
    ):
        await service.logout('refresh-token')

    revoke.assert_awaited_once_with(token)
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_does_nothing_for_unknown_token(
    service: AuthService,
) -> None:
    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'unknown-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            service.refresh_tokens,
            'revoke',
            new_callable=AsyncMock,
        ) as revoke,
    ):
        await service.logout('unknown-token')

    revoke.assert_not_awaited()
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_logout_does_nothing_without_token(
    service: AuthService,
) -> None:
    with patch.object(
        service.refresh_tokens,
        'get_by_hash',
        new_callable=AsyncMock,
    ) as get_by_hash:
        await service.logout(None)

    get_by_hash.assert_not_awaited()
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_logout_ignores_unknown_refresh_token(
    service: AuthService,
) -> None:
    with (
        patch(
            'services.auth.hash_refresh_token',
            return_value=b'unknown-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            service.refresh_tokens,
            'revoke',
            new_callable=AsyncMock,
        ) as revoke,
    ):
        await service.logout(
            refresh_token='unknown-token',
        )

    revoke.assert_not_awaited()
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_logout_all_revokes_all_user_tokens(
    service: AuthService,
) -> None:
    user_id = uuid4()

    with patch.object(
        service.refresh_tokens,
        'revoke_all_for_user',
        new_callable=AsyncMock,
    ) as revoke_all:
        await service.logout_all(user_id)

    revoke_all.assert_awaited_once_with(user_id)
    service.session.commit.assert_awaited_once()
