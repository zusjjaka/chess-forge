import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)


def test_register_request_valid():
    data = RegisterRequest(
        email='test@example.com',
        password='password123',
        password_repeat='password123',
    )

    assert data.email == 'test@example.com'
    assert data.password == 'password123'
    assert data.password_repeat == 'password123'


def test_register_request_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email='invalid-email',
            password='password123',
            password_repeat='password123',
        )


def test_register_request_password_too_short():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email='test@example.com',
            password='1234567',
            password_repeat='1234567',
        )


def test_register_request_password_too_long():
    password = 'a' * 129

    with pytest.raises(ValidationError):
        RegisterRequest(
            email='test@example.com',
            password=password,
            password_repeat=password,
        )


def test_register_request_passwords_do_not_match():
    with pytest.raises(ValidationError, match='Passwords do not match'):
        RegisterRequest(
            email='test@example.com',
            password='password123',
            password_repeat='different123',
        )


def test_login_request_valid():
    data = LoginRequest(
        email='test@example.com',
        password='password123',
    )

    assert data.email == 'test@example.com'
    assert data.password == 'password123'


def test_token_response_default_token_type():
    data = TokenResponse(
        access_token='token',
        expires_in=180,
    )

    assert data.access_token == 'token'
    assert data.token_type == 'bearer'
    assert data.expires_in == 180


def test_register_response():
    user_id = uuid.uuid4()

    data = RegisterResponse(
        id=user_id,
        email='test@example.com',
        status='active',
    )

    assert data.id == user_id
    assert data.email == 'test@example.com'
    assert data.status == 'active'


def test_user_response():
    user_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    data = UserResponse(
        id=user_id,
        email='test@example.com',
        display_name='Test',
        is_email_verified=False,
        created_at=created_at,
    )

    assert data.id == user_id
    assert data.email == 'test@example.com'
    assert data.display_name == 'Test'
    assert data.is_email_verified is False
    assert data.created_at == created_at
