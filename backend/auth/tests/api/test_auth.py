import pytest

REGISTER_URL = '/api/v1/auth/register'
LOGIN_URL = '/api/v1/auth/login'
REFRESH_URL = '/api/v1/auth/tokens/refresh'


@pytest.mark.asyncio
async def test_register(client):
    response = await client.post(
        REGISTER_URL,
        json={
            'email': 'test@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert 'id' in data
    assert data['email'] == 'test@example.com'
    assert data['status'] == 'pending_verification'


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    response = await client.post(
        REGISTER_URL,
        json={
            'email': 'not-an-email',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_passwords_do_not_match(client):
    response = await client.post(
        REGISTER_URL,
        json={
            'email': 'test@example.com',
            'password': 'password123',
            'password_repeat': 'different123',
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        'email': 'test@example.com',
        'password': 'password123',
        'password_repeat': 'password123',
    }

    first_response = await client.post(
        REGISTER_URL,
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = await client.post(
        REGISTER_URL,
        json=payload,
    )

    assert second_response.status_code == 409
    assert 'detail' in second_response.json()


@pytest.mark.asyncio
async def test_login(client):
    await client.post(
        REGISTER_URL,
        json={
            'email': 'test@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    response = await client.post(
        LOGIN_URL,
        json={
            'email': 'test@example.com',
            'password': 'password123',
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data['access_token']
    assert data['token_type'] == 'bearer'
    assert data['expires_in'] == 180

    assert 'refresh_token' in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post(
        REGISTER_URL,
        json={
            'email': 'test@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    response = await client.post(
        LOGIN_URL,
        json={
            'email': 'test@example.com',
            'password': 'wrong-password',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid credentials'


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    response = await client.post(
        LOGIN_URL,
        json={
            'email': 'unknown@example.com',
            'password': 'password123',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid credentials'


@pytest.mark.asyncio
async def test_refresh_without_cookie(client):
    response = await client.post(REFRESH_URL)

    assert response.status_code == 401
    assert response.json()['detail'] == 'Refresh token missing'


@pytest.mark.asyncio
async def test_refresh(client):
    await client.post(
        REGISTER_URL,
        json={
            'email': 'test@example.com',
            'password': 'password123',
            'password_repeat': 'password123',
        },
    )

    login_response = await client.post(
        LOGIN_URL,
        json={
            'email': 'test@example.com',
            'password': 'password123',
        },
    )

    assert login_response.status_code == 200

    old_access_token = login_response.json()['access_token']
    old_refresh_token = login_response.cookies['refresh_token']

    # secure=True means the cookie is normally sent only over HTTPS.
    # Set it manually for the test client.
    client.cookies.set(
        'refresh_token',
        old_refresh_token,
        path='/api/v1/auth/',
    )

    response = await client.post(REFRESH_URL)

    assert response.status_code == 200

    data = response.json()

    assert data['access_token']
    assert data['access_token'] != old_access_token
    assert data['token_type'] == 'bearer'
    assert data['expires_in'] == 180

    new_refresh_token = response.cookies.get('refresh_token')

    assert new_refresh_token
    assert new_refresh_token != old_refresh_token
