import pytest
from pydantic import ValidationError

from schemas.auth import (
    LoginRequest,
    RegisterRequest,
)


class TestRegisterRequest:
    def test_valid_data(self) -> None:
        data = RegisterRequest(
            email='user@example.com',
            password='password123',
            password_repeat='password123',
        )

        assert data.email == 'user@example.com'
        assert data.password == 'password123'
        assert data.password_repeat == 'password123'

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(
                email='not-an-email',
                password='password123',
                password_repeat='password123',
            )

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(
                email='user@example.com',
                password='short',
                password_repeat='short',
            )

    def test_password_too_long(self) -> None:
        password = 'a' * 129

        with pytest.raises(ValidationError):
            RegisterRequest(
                email='user@example.com',
                password=password,
                password_repeat=password,
            )

    def test_passwords_do_not_match(self) -> None:
        with pytest.raises(
            ValueError,
            match='Passwords do not match',
        ):
            RegisterRequest(
                email='user@example.com',
                password='password123',
                password_repeat='password456',
            )


class TestLoginRequest:
    def test_valid_data(self) -> None:
        data = LoginRequest(
            email='user@example.com',
            password='password123',
        )

        assert data.email == 'user@example.com'
        assert data.password == 'password123'

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(
                email='not-an-email',
                password='password123',
            )
