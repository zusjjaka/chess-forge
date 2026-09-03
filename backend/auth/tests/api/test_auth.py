from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import (
    get_current_user,
    get_db_session,
    get_email_publisher,
)
from core.config import get_settings
from main import app
from models.refresh_token import RefreshToken
from models.user import User
from models.verification_code import (
    EmailVerificationCode,
    PasswordResetCode,
)


settings = get_settings()

settings.refresh_token_cookie.secure = False


class FakeEmailPublisher:
    def __init__(self) -> None:
        self.publish_email_verification = AsyncMock()
        self.publish_password_reset = AsyncMock()


@pytest_asyncio.fixture
async def email_publisher() -> AsyncGenerator[FakeEmailPublisher]:
    yield FakeEmailPublisher()


@pytest_asyncio.fixture
async def client(
    session: AsyncSession,
    email_publisher: FakeEmailPublisher,
) -> AsyncGenerator[AsyncClient]:
    def override_get_db_session():
        yield session

    def override_get_email_publisher() -> FakeEmailPublisher:
        return email_publisher

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[
        get_email_publisher
    ] = override_get_email_publisher

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        yield client

    app.dependency_overrides.clear()


async def register_user(
    client: AsyncClient,
    email: str = 'user@example.com',
    password: str = 'password123',
) -> None:
    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': email,
            'password': password,
            'password_repeat': password,
        },
    )

    assert response.status_code == 201


async def login_user(
    client: AsyncClient,
    email: str = 'user@example.com',
    password: str = 'password123',
) -> dict:
    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': email,
            'password': password,
        },
    )

    assert response.status_code == 200

    return response.json()


async def get_user(
    session: AsyncSession,
    email: str = 'user@example.com',
) -> User:
    result = await session.execute(
        select(User).where(User.email == email),
    )

    return result.scalar_one()


# ============================================================================
# POST /api/v1/auth/register
# ============================================================================


@pytest.mark.asyncio
async def test_register(
    client: AsyncClient,
    email_publisher: FakeEmailPublisher,
) -> None:
    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data['id']
    assert data['email'] == 'user@example.com'
    assert data['status'] == 'pending_verification'

    email_publisher.publish_email_verification.assert_awaited_once()

    call = email_publisher.publish_email_verification.await_args

    assert call.kwargs['email'] == 'user@example.com'
    assert call.kwargs['code']
    assert call.kwargs['message_id']


@pytest.mark.asyncio
async def test_register_rejects_verified_duplicate_email(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await register_user(client)

    user = await get_user(session)
    user.is_email_verified = True
    await session.commit()

    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    assert response.status_code == 409
    assert 'user@example.com' in response.json()['detail']


@pytest.mark.asyncio
async def test_register_updates_unverified_existing_user(
    client: AsyncClient,
    session: AsyncSession,
    email_publisher: FakeEmailPublisher,
) -> None:
    await register_user(client)

    user_before = await get_user(session)

    email_publisher.publish_email_verification.reset_mock()

    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'newpassword123',
            'password_repeat': 'newpassword123',
        },
    )

    assert response.status_code == 201

    user_after = await get_user(session)

    assert user_after.id == user_before.id
    assert user_after.is_email_verified is False

    email_publisher.publish_email_verification.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_rejects_password_mismatch(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'different123',
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_invalid_email(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'not-an-email',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_short_password(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'short',
            'password_repeat': 'short',
        },
    )

    assert response.status_code == 422


# ============================================================================
# POST /api/v1/auth/login
# ============================================================================


@pytest.mark.asyncio
async def test_login(
    client: AsyncClient,
) -> None:
    await register_user(client)

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'password123',
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data['access_token']
    assert data['token_type'] == 'bearer'
    assert data['expires_in'] > 0

    cookie_name = settings.refresh_token_cookie.name

    assert cookie_name in response.cookies
    assert cookie_name in client.cookies


@pytest.mark.asyncio
async def test_login_rejects_unknown_user(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'unknown@example.com',
            'password': 'password123',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid credentials'


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(
    client: AsyncClient,
) -> None:
    await register_user(client)

    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'wrong-password',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid credentials'


@pytest.mark.asyncio
async def test_login_rejects_invalid_email_format(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'not-an-email',
            'password': 'password123',
        },
    )

    assert response.status_code == 422


# ============================================================================
# POST /api/v1/auth/tokens/refresh
# ============================================================================


@pytest.mark.asyncio
async def test_refresh(
    client: AsyncClient,
) -> None:
    await register_user(client)
    await login_user(client)

    cookie_name = settings.refresh_token_cookie.name

    assert cookie_name in client.cookies

    old_refresh_token = client.cookies[cookie_name]

    response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert response.status_code == 200

    data = response.json()

    assert data['access_token']
    assert data['token_type'] == 'bearer'
    assert data['expires_in'] > 0

    new_refresh_token = client.cookies[cookie_name]

    assert new_refresh_token != old_refresh_token


@pytest.mark.asyncio
async def test_refresh_rejects_missing_token(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid refresh token'


@pytest.mark.asyncio
async def test_refresh_rejects_invalid_token(
    client: AsyncClient,
) -> None:
    cookie_name = settings.refresh_token_cookie.name

    client.cookies.set(
        cookie_name,
        'invalid-refresh-token',
    )

    response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid refresh token'


@pytest.mark.asyncio
async def test_refresh_rejects_expired_token(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await register_user(client)
    await login_user(client)

    cookie_name = settings.refresh_token_cookie.name
    refresh_token = client.cookies[cookie_name]

    result = await session.execute(
        select(RefreshToken),
    )
    stored_token = result.scalar_one()

    stored_token.expires_at = datetime.now(UTC) - timedelta(minutes=1)

    await session.commit()

    client.cookies.set(
        cookie_name,
        refresh_token,
    )

    response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Refresh token expired'

    await session.refresh(stored_token)

    assert stored_token.is_active is False
    assert stored_token.revoked_at is not None


@pytest.mark.asyncio
async def test_refresh_detects_token_reuse(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await register_user(client)
    await login_user(client)

    cookie_name = settings.refresh_token_cookie.name
    old_refresh_token = client.cookies[cookie_name]

    first_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert first_response.status_code == 200

    client.cookies.set(
        cookie_name,
        old_refresh_token,
    )

    reuse_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert reuse_response.status_code == 401
    assert reuse_response.json()['detail'] == 'Refresh token reuse detected'

    result = await session.execute(
        select(RefreshToken),
    )
    tokens = result.scalars().all()

    assert tokens
    assert all(token.is_active is False for token in tokens)


@pytest.mark.asyncio
async def test_refresh_rotates_token_in_database(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await register_user(client)
    await login_user(client)

    result = await session.execute(
        select(RefreshToken),
    )
    old_token = result.scalar_one()

    old_token_id = old_token.id

    response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert response.status_code == 200

    result = await session.execute(
        select(RefreshToken),
    )
    tokens = result.scalars().all()

    assert len(tokens) == 2

    old_token = next(
        token for token in tokens
        if token.id == old_token_id
    )

    new_token = next(
        token for token in tokens
        if token.id != old_token_id
    )

    assert old_token.is_active is False
    assert old_token.revoked_at is not None
    assert old_token.replaced_by == new_token.id

    assert new_token.is_active is True
    assert new_token.family_id == old_token.family_id


# ============================================================================
# POST /api/v1/auth/logout
# ============================================================================


@pytest.mark.asyncio
async def test_logout(
    client: AsyncClient,
) -> None:
    await register_user(client)
    await login_user(client)

    cookie_name = settings.refresh_token_cookie.name

    assert cookie_name in client.cookies

    response = await client.post(
        '/api/v1/auth/logout',
    )

    assert response.status_code == 204
    assert cookie_name not in client.cookies


@pytest.mark.asyncio
async def test_logout_without_token(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/logout',
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_with_invalid_token(
    client: AsyncClient,
) -> None:
    cookie_name = settings.refresh_token_cookie.name

    client.cookies.set(
        cookie_name,
        'invalid-refresh-token',
    )

    response = await client.post(
        '/api/v1/auth/logout',
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(
    client: AsyncClient,
) -> None:
    await register_user(client)
    await login_user(client)

    cookie_name = settings.refresh_token_cookie.name
    refresh_token = client.cookies[cookie_name]

    response = await client.post(
        '/api/v1/auth/logout',
    )

    assert response.status_code == 204

    client.cookies.set(
        cookie_name,
        refresh_token,
    )

    refresh_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json()['detail'] == 'Refresh token reuse detected'


# ============================================================================
# POST /api/v1/auth/logout-all
# ============================================================================


@pytest.mark.asyncio
async def test_logout_all(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await register_user(client)
    login_data = await login_user(client)

    user = await get_user(session)

    user.is_email_verified = True
    await session.commit()

    access_token = login_data['access_token']

    cookie_name = settings.refresh_token_cookie.name
    refresh_token = client.cookies[cookie_name]

    response = await client.post(
        '/api/v1/auth/logout-all',
        headers={
            'Authorization': f'Bearer {access_token}',
        },
    )

    assert response.status_code == 204

    client.cookies.set(
        cookie_name,
        refresh_token,
    )

    refresh_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_revokes_all_user_tokens(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await register_user(client)

    first_login = await login_user(client)

    cookie_name = settings.refresh_token_cookie.name
    client.cookies.clear()

    second_login = await login_user(client)

    user = await get_user(session)

    user.is_email_verified = True
    await session.commit()

    response = await client.post(
        '/api/v1/auth/logout-all',
        headers={
            'Authorization': f"Bearer {first_login['access_token']}",
        },
    )

    assert response.status_code == 204

    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
        ),
    )
    tokens = result.scalars().all()

    assert len(tokens) == 2
    assert all(token.is_active is False for token in tokens)

    client.cookies.set(
        cookie_name,
        client.cookies[cookie_name],
    )

    refresh_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert refresh_response.status_code == 401

    assert second_login['access_token']


@pytest.mark.asyncio
async def test_logout_all_rejects_missing_access_token(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/logout-all',
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_rejects_invalid_access_token(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/logout-all',
        headers={
            'Authorization': 'Bearer invalid-token',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid access token'


@pytest.mark.asyncio
async def test_logout_all_rejects_unverified_user(
    client: AsyncClient,
) -> None:
    await register_user(client)

    login_data = await login_user(client)

    response = await client.post(
        '/api/v1/auth/logout-all',
        headers={
            'Authorization': (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Email is not verified'


# ============================================================================
# GET /api/v1/auth/me
# ============================================================================


@pytest.mark.asyncio
async def test_me(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    user = User(
        email='user@example.com',
        password_hash='hashed-password',
        display_name=None,
        is_email_verified=True,
    )

    session.add(user)
    await session.flush()

    def override_get_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        response = await client.get(
            '/api/v1/auth/me',
        )

        assert response.status_code == 200

        data = response.json()

        assert data['email'] == user.email
        assert data['display_name'] is None
        assert 'created_at' in data

        assert set(data) == {
            'email',
            'display_name',
            'created_at',
        }
    finally:
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


@pytest.mark.asyncio
async def test_me_rejects_missing_access_token(
    client: AsyncClient,
) -> None:
    response = await client.get(
        '/api/v1/auth/me',
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_invalid_access_token(
    client: AsyncClient,
) -> None:
    response = await client.get(
        '/api/v1/auth/me',
        headers={
            'Authorization': 'Bearer invalid-token',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid access token'


@pytest.mark.asyncio
async def test_me_rejects_unverified_user(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    await register_user(client)

    login_data = await login_user(client)

    response = await client.get(
        '/api/v1/auth/me',
        headers={
            'Authorization': (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Email is not verified'


# ============================================================================
# POST /api/v1/auth/email/approval
# ============================================================================


@pytest.mark.asyncio
async def test_email_approval(
    client: AsyncClient,
    session: AsyncSession,
    email_publisher: FakeEmailPublisher,
) -> None:
    await register_user(client)

    email_publisher.publish_email_verification.assert_awaited_once()

    call = email_publisher.publish_email_verification.await_args

    verification_code = call.kwargs['code']

    login_data = await login_user(client)

    response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': verification_code,
        },
        headers={
            'Authorization': (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert response.status_code == 204
    assert response.content == b''

    user = await get_user(session)

    assert user.is_email_verified is True

    result = await session.execute(
        select(EmailVerificationCode).where(
            EmailVerificationCode.user_id == user.id,
        ),
    )
    stored_code = result.scalar_one()

    assert stored_code.used_at is not None


@pytest.mark.asyncio
async def test_email_approval_rejects_invalid_code(
    client: AsyncClient,
) -> None:
    await register_user(client)

    login_data = await login_user(client)

    response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': '000000',
        },
        headers={
            'Authorization': (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()['detail'] == (
        'Invalid or expired verification code'
    )


@pytest.mark.asyncio
async def test_email_approval_rejects_expired_code(
    client: AsyncClient,
    session: AsyncSession,
    email_publisher: FakeEmailPublisher,
) -> None:
    await register_user(client)

    call = email_publisher.publish_email_verification.await_args
    verification_code = call.kwargs['code']

    result = await session.execute(
        select(EmailVerificationCode),
    )
    stored_code = result.scalar_one()

    stored_code.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await session.commit()

    login_data = await login_user(client)

    response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': verification_code,
        },
        headers={
            'Authorization': (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()['detail'] == (
        'Invalid or expired verification code'
    )

    user = await get_user(session)

    assert user.is_email_verified is False


@pytest.mark.asyncio
async def test_email_approval_rejects_reused_code(
    client: AsyncClient,
    email_publisher: FakeEmailPublisher,
) -> None:
    await register_user(client)

    call = email_publisher.publish_email_verification.await_args
    verification_code = call.kwargs['code']

    login_data = await login_user(client)

    headers = {
        'Authorization': (
            f"Bearer {login_data['access_token']}"
        ),
    }

    first_response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': verification_code,
        },
        headers=headers,
    )

    assert first_response.status_code == 204

    second_response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': verification_code,
        },
        headers=headers,
    )

    assert second_response.status_code == 400
    assert second_response.json()['detail'] == (
        'Invalid or expired verification code'
    )


@pytest.mark.asyncio
async def test_email_approval_rejects_invalid_code_format(
    client: AsyncClient,
) -> None:
    await register_user(client)

    login_data = await login_user(client)

    response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': '12345',
        },
        headers={
            'Authorization': (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_email_approval_rejects_non_numeric_code(
    client: AsyncClient,
) -> None:
    await register_user(client)

    login_data = await login_user(client)

    response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': 'abcdef',
        },
        headers={
            'Authorization': (
                f"Bearer {login_data['access_token']}"
            ),
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_email_approval_rejects_missing_access_token(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': '123456',
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_email_approval_rejects_invalid_access_token(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/email/approval',
        json={
            'code': '123456',
        },
        headers={
            'Authorization': 'Bearer invalid-token',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid access token'


# ============================================================================
# POST /api/v1/auth/password/reset/request
# ============================================================================


@pytest.mark.asyncio
async def test_request_password_reset(
    client: AsyncClient,
    email_publisher: FakeEmailPublisher,
) -> None:
    await register_user(client)

    response = await client.post(
        '/api/v1/auth/password/reset/request',
        json={
            'email': 'user@example.com',
        },
    )

    assert response.status_code == 202

    email_publisher.publish_password_reset.assert_awaited_once()

    call = email_publisher.publish_password_reset.await_args

    assert call.kwargs['email'] == 'user@example.com'
    assert call.kwargs['code']
    assert len(call.kwargs['code']) == 6
    assert call.kwargs['message_id']


@pytest.mark.asyncio
async def test_request_password_reset_for_unknown_email(
    client: AsyncClient,
    email_publisher: FakeEmailPublisher,
) -> None:
    response = await client.post(
        '/api/v1/auth/password/reset/request',
        json={
            'email': 'unknown@example.com',
        },
    )

    assert response.status_code == 202

    email_publisher.publish_password_reset.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_password_reset_rejects_invalid_email(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/password/reset/request',
        json={
            'email': 'not-an-email',
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_confirm_password_reset(
    client: AsyncClient,
    session: AsyncSession,
    email_publisher: FakeEmailPublisher,
) -> None:
    await register_user(client)
    await login_user(client)

    cookie_name = settings.refresh_token_cookie.name
    old_refresh_token = client.cookies[cookie_name]

    await client.post(
        '/api/v1/auth/password/reset/request',
        json={
            'email': 'user@example.com',
        },
    )

    call = email_publisher.publish_password_reset.await_args
    reset_code = call.kwargs['code']

    response = await client.post(
        '/api/v1/auth/password/reset/confirm',
        json={
            'email': 'user@example.com',
            'code': reset_code,
            'password': 'newpassword123',
            'password_repeat': 'newpassword123',
        },
    )

    assert response.status_code == 204
    assert response.content == b''

    user = await get_user(session)

    assert user.password_hash != 'password123'

    result = await session.execute(
        select(PasswordResetCode).where(
            PasswordResetCode.user_id == user.id,
        ),
    )
    reset_code_model = result.scalar_one()

    assert reset_code_model.used_at is not None

    client.cookies.set(
        cookie_name,
        old_refresh_token,
    )

    refresh_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json()['detail'] == (
        'Refresh token reuse detected'
    )

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'newpassword123',
        },
    )

    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_confirm_password_reset_rejects_invalid_code(
    client: AsyncClient,
    email_publisher: FakeEmailPublisher,
) -> None:
    await register_user(client)

    await client.post(
        '/api/v1/auth/password/reset/request',
        json={
            'email': 'user@example.com',
        },
    )

    response = await client.post(
        '/api/v1/auth/password/reset/confirm',
        json={
            'email': 'user@example.com',
            'code': '000000',
            'password': 'newpassword123',
            'password_repeat': 'newpassword123',
        },
    )

    assert response.status_code == 400
    assert response.json()['detail'] == (
        'Invalid or expired verification code'
    )


@pytest.mark.asyncio
async def test_confirm_password_reset_rejects_invalid_code_format(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/password/reset/confirm',
        json={
            'email': 'user@example.com',
            'code': '12345',
            'password': 'newpassword123',
            'password_repeat': 'newpassword123',
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_confirm_password_reset_rejects_password_mismatch(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/password/reset/confirm',
        json={
            'email': 'user@example.com',
            'code': '123456',
            'password': 'newpassword123',
            'password_repeat': 'different123',
        },
    )

    assert response.status_code == 422
