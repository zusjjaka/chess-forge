import pytest

REGISTER_URL = '/api/v1/auth/register'
LOGIN_URL = '/api/v1/auth/login'
ME_URL = '/api/v1/auth/me'


@pytest.mark.asyncio
async def test_get_current_user(client):
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

    access_token = login_response.json()['access_token']

    response = await client.get(
        ME_URL,
        headers={
            'Authorization': f'Bearer {access_token}',
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data['email'] == 'test@example.com'
    assert data['display_name'] is None
    assert data['is_email_verified'] is False
    assert 'id' in data
    assert 'created_at' in data


@pytest.mark.asyncio
async def test_get_current_user_without_token(client):
    response = await client.get(ME_URL)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client):
    response = await client.get(
        ME_URL,
        headers={
            'Authorization': 'Bearer invalid-token',
        },
    )

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid access token'


@pytest.mark.asyncio
async def test_get_current_user_malformed_authorization(client):
    response = await client.get(
        ME_URL,
        headers={
            'Authorization': 'NotBearer token',
        },
    )

    assert response.status_code == 403
