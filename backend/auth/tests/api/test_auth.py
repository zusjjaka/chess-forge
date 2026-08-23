from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from core.config import get_settings
from db.session import get_db_session
from main import app
from models.user import User

settings = get_settings()

# HTTP-клиент в тестах не работает с Secure cookies по обычному HTTP.
settings.refresh_token_cookie.secure = False


@pytest.fixture
async def client(
    session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register(
    client: AsyncClient,
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

    assert data['email'] == 'user@example.com'
    assert data['status'] == 'pending_verification'
    assert 'id' in data


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(
    client: AsyncClient,
) -> None:
    payload = {
        'email': 'user@example.com',
        'password': 'password123',
        'password_repeat': 'password123',
    }

    first_response = await client.post(
        '/api/v1/auth/register',
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        '/api/v1/auth/register',
        json=payload,
    )

    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_login(
    client: AsyncClient,
) -> None:
    await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

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

    assert settings.refresh_token_cookie.name in response.cookies


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(
    client: AsyncClient,
) -> None:
    response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'unknown@example.com',
            'password': 'wrong-password',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid credentials'


@pytest.mark.asyncio
async def test_refresh(
    client: AsyncClient,
) -> None:
    await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'password123',
        },
    )

    assert login_response.status_code == 200

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
    assert response.json()['detail'] == 'Refresh token missing'


@pytest.mark.asyncio
async def test_logout(
    client: AsyncClient,
) -> None:
    await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'password123',
        },
    )

    assert login_response.status_code == 200

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
async def test_logout_invalidates_refresh_token(
    client: AsyncClient,
) -> None:
    await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'password123',
        },
    )

    assert login_response.status_code == 200

    response = await client.post(
        '/api/v1/auth/logout',
    )

    assert response.status_code == 204

    refresh_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert refresh_response.status_code == 401


@pytest.mark.asyncio
async def test_me(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    user = User(
        email='user@example.com',
        password_hash='hashed-password',
    )

    session.add(user)
    await session.flush()

    def override_get_current_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user

    response = await client.get('/api/v1/auth/me')

    assert response.status_code == 200

    data = response.json()

    assert data['id'] == str(user.id)
    assert data['email'] == user.email
    assert data['display_name'] is None
    assert data['is_email_verified'] is False
    assert 'created_at' in data


@pytest.mark.asyncio
async def test_logout_all(
    client: AsyncClient,
) -> None:
    await client.post(
        '/api/v1/auth/register',
        json={
            'email': 'user@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    login_response = await client.post(
        '/api/v1/auth/login',
        json={
            'email': 'user@example.com',
            'password': 'password123',
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()['access_token']

    cookie_name = settings.refresh_token_cookie.name
    assert cookie_name in client.cookies

    response = await client.post(
        '/api/v1/auth/logout-all',
        headers={
            'Authorization': f'Bearer {access_token}',
        },
    )

    assert response.status_code == 204

    refresh_response = await client.post(
        '/api/v1/auth/tokens/refresh',
    )

    assert refresh_response.status_code == 401
