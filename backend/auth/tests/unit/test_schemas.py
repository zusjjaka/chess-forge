import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from schemas.auth import (
    EmailApprovalRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from schemas.email import (
    EmailMessage,
    EmailVerificationData,
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


class TestRegisterResponse:
    def test_valid_data(self) -> None:
        user_id = uuid.uuid4()

        data = RegisterResponse(
            id=user_id,
            email='user@example.com',
            status='pending_verification',
        )

        assert data.id == user_id
        assert data.email == 'user@example.com'
        assert data.status == 'pending_verification'

    def test_invalid_id(self) -> None:
        with pytest.raises(ValidationError):
            RegisterResponse(
                id='not-a-uuid',
                email='user@example.com',
                status='pending_verification',
            )

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            RegisterResponse(
                id=uuid.uuid4(),
                email='not-an-email',
                status='pending_verification',
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


class TestTokenResponse:
    def test_valid_data(self) -> None:
        data = TokenResponse(
            access_token='access-token',
            expires_in=180,
        )

        assert data.access_token == 'access-token'
        assert data.token_type == 'bearer'
        assert data.expires_in == 180

    def test_custom_token_type(self) -> None:
        data = TokenResponse(
            access_token='access-token',
            token_type='custom',
            expires_in=180,
        )

        assert data.token_type == 'custom'

    def test_missing_access_token(self) -> None:
        with pytest.raises(ValidationError):
            TokenResponse(
                expires_in=180,
            )

    def test_missing_expires_in(self) -> None:
        with pytest.raises(ValidationError):
            TokenResponse(
                access_token='access-token',
            )


class TestUserResponse:
    def test_valid_data(self) -> None:
        created_at = datetime.now(UTC)

        data = UserResponse(
            email='user@example.com',
            display_name='Test User',
            created_at=created_at,
        )

        assert data.email == 'user@example.com'
        assert data.display_name == 'Test User'
        assert data.created_at == created_at

    def test_nullable_display_name(self) -> None:
        data = UserResponse(
            email='user@example.com',
            display_name=None,
            created_at=datetime.now(UTC),
        )

        assert data.display_name is None

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserResponse(
                email='not-an-email',
                display_name='Test User',
                created_at=datetime.now(UTC),
            )

    def test_from_attributes(self) -> None:
        class UserModel:
            email = 'user@example.com'
            display_name = 'Test User'
            created_at = datetime.now(UTC)

        data = UserResponse.model_validate(
            UserModel(),
            from_attributes=True,
        )

        assert data.email == UserModel.email
        assert data.display_name == UserModel.display_name
        assert data.created_at == UserModel.created_at


class TestEmailApprovalRequest:
    def test_valid_code(self) -> None:
        data = EmailApprovalRequest(code='123456')

        assert data.code == '123456'

    def test_code_too_short(self) -> None:
        with pytest.raises(ValidationError):
            EmailApprovalRequest(code='12345')

    def test_code_too_long(self) -> None:
        with pytest.raises(ValidationError):
            EmailApprovalRequest(code='1234567')

    def test_code_must_contain_only_digits(self) -> None:
        with pytest.raises(ValidationError):
            EmailApprovalRequest(code='12345a')

    def test_code_must_not_contain_spaces(self) -> None:
        with pytest.raises(ValidationError):
            EmailApprovalRequest(code='123 56')


class TestEmailVerificationData:
    def test_valid_code(self) -> None:
        data = EmailVerificationData(code='123456')

        assert data.code == '123456'

    def test_code_too_short(self) -> None:
        with pytest.raises(ValidationError):
            EmailVerificationData(code='12345')

    def test_code_too_long(self) -> None:
        with pytest.raises(ValidationError):
            EmailVerificationData(code='1234567')

    def test_code_must_contain_only_digits(self) -> None:
        with pytest.raises(ValidationError):
            EmailVerificationData(code='12345a')

    def test_code_must_not_contain_spaces(self) -> None:
        with pytest.raises(ValidationError):
            EmailVerificationData(code='123 56')


class TestEmailMessage:
    def test_valid_data(self) -> None:
        message_id = uuid.uuid4()

        data = EmailMessage(
            type='email.verification',
            to='user@example.com',
            data={'code': '123456'},
            message_id=message_id,
        )

        assert data.type == 'email.verification'
        assert data.to == 'user@example.com'
        assert data.data == {'code': '123456'}
        assert data.message_id == message_id
        assert data.version == 1

    def test_custom_version(self) -> None:
        data = EmailMessage(
            type='email.verification',
            to='user@example.com',
            data={'code': '123456'},
            message_id=uuid.uuid4(),
            version=2,
        )

        assert data.version == 2

    def test_invalid_type(self) -> None:
        with pytest.raises(ValidationError):
            EmailMessage(
                type='email.unknown',
                to='user@example.com',
                data={'code': '123456'},
                message_id=uuid.uuid4(),
            )

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            EmailMessage(
                type='email.verification',
                to='not-an-email',
                data={'code': '123456'},
                message_id=uuid.uuid4(),
            )

    def test_invalid_message_id(self) -> None:
        with pytest.raises(ValidationError):
            EmailMessage(
                type='email.verification',
                to='user@example.com',
                data={'code': '123456'},
                message_id='not-a-uuid',
            )


class TestPasswordResetRequest:
    def test_valid_data(self) -> None:
        data = PasswordResetRequest(
            email='user@example.com',
        )

        assert data.email == 'user@example.com'

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            PasswordResetRequest(
                email='not-an-email',
            )


class TestPasswordResetConfirm:
    def test_valid_data(self) -> None:
        data = PasswordResetConfirm(
            email='user@example.com',
            code='123456',
            password='password123',
            password_repeat='password123',
        )

        assert data.email == 'user@example.com'
        assert data.code == '123456'
        assert data.password == 'password123'
        assert data.password_repeat == 'password123'

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            PasswordResetConfirm(
                email='not-an-email',
                code='123456',
                password='password123',
                password_repeat='password123',
            )

    def test_code_too_short(self) -> None:
        with pytest.raises(ValidationError):
            PasswordResetConfirm(
                email='user@example.com',
                code='12345',
                password='password123',
                password_repeat='password123',
            )

    def test_code_too_long(self) -> None:
        with pytest.raises(ValidationError):
            PasswordResetConfirm(
                email='user@example.com',
                code='1234567',
                password='password123',
                password_repeat='password123',
            )

    def test_code_must_contain_only_digits(self) -> None:
        with pytest.raises(ValidationError):
            PasswordResetConfirm(
                email='user@example.com',
                code='12345a',
                password='password123',
                password_repeat='password123',
            )

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            PasswordResetConfirm(
                email='user@example.com',
                code='123456',
                password='short',
                password_repeat='short',
            )

    def test_password_too_long(self) -> None:
        password = 'a' * 129

        with pytest.raises(ValidationError):
            PasswordResetConfirm(
                email='user@example.com',
                code='123456',
                password=password,
                password_repeat=password,
            )

    def test_passwords_do_not_match(self) -> None:
        with pytest.raises(
            ValueError,
            match='Passwords do not match',
        ):
            PasswordResetConfirm(
                email='user@example.com',
                code='123456',
                password='password123',
                password_repeat='password456',
            )
