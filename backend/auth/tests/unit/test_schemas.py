import uuid
from datetime import (
    UTC,
    datetime,
    date,
    timedelta,
)

import pytest
from pydantic import ValidationError

from models.user import Gender
from schemas.auth import (
    EmailApprovalRequest,
    EmailChangeConfirm,
    EmailChangeRequest,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
    UserUpdateResponse,
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
            gender=Gender.MALE,
            country='KZ',
            birth_date=date(2000, 1, 1),
            bio='Test bio',
            telegram_alias='test_user',
            created_at=created_at,
        )

        assert data.email == 'user@example.com'
        assert data.display_name == 'Test User'
        assert data.gender == Gender.MALE
        assert data.country == 'KZ'
        assert data.birth_date == date(2000, 1, 1)
        assert data.bio == 'Test bio'
        assert data.telegram_alias == 'test_user'
        assert data.created_at == created_at

    def test_nullable_fields(self) -> None:
        data = UserResponse(
            email='user@example.com',
            display_name=None,
            gender=None,
            country=None,
            birth_date=None,
            bio=None,
            telegram_alias=None,
            created_at=datetime.now(UTC),
        )

        assert data.display_name is None
        assert data.gender is None
        assert data.country is None
        assert data.birth_date is None
        assert data.bio is None
        assert data.telegram_alias is None

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserResponse(
                email='not-an-email',
                display_name='Test User',
                gender=Gender.MALE,
                country='KZ',
                birth_date=date(2000, 1, 1),
                bio='Test bio',
                telegram_alias='test_user',
                created_at=datetime.now(UTC),
            )

    def test_from_attributes(self) -> None:
        class UserModel:
            email = 'user@example.com'
            display_name = 'Test User'
            gender = Gender.MALE
            country = 'KZ'
            birth_date = date(2000, 1, 1)
            bio = 'Test bio'
            telegram_alias = 'test_user'
            created_at = datetime.now(UTC)

        data = UserResponse.model_validate(
            UserModel(),
            from_attributes=True,
        )

        assert data.email == UserModel.email
        assert data.display_name == UserModel.display_name
        assert data.gender == UserModel.gender
        assert data.country == UserModel.country
        assert data.birth_date == UserModel.birth_date
        assert data.bio == UserModel.bio
        assert data.telegram_alias == UserModel.telegram_alias
        assert data.created_at == UserModel.created_at


class TestUserUpdateRequest:
    def test_valid_data(self) -> None:
        data = UserUpdateRequest(
            display_name='Test User',
            gender=Gender.MALE,
            country='KZ',
            birth_date=date.today() - timedelta(days=365 * 20),
            bio='Test bio',
            telegram_alias='test_user',
        )

        assert data.display_name == 'Test User'
        assert data.gender == Gender.MALE
        assert data.country == 'KZ'
        assert data.bio == 'Test bio'
        assert data.telegram_alias == 'test_user'

    def test_all_fields_are_optional(self) -> None:
        data = UserUpdateRequest()

        assert data.display_name is None
        assert data.gender is None
        assert data.country is None
        assert data.birth_date is None
        assert data.bio is None
        assert data.telegram_alias is None

    def test_nullable_fields(self) -> None:
        data = UserUpdateRequest(
            display_name=None,
            gender=None,
            country=None,
            birth_date=None,
            bio=None,
            telegram_alias=None,
        )

        assert data.display_name is None
        assert data.gender is None
        assert data.country is None
        assert data.birth_date is None
        assert data.bio is None
        assert data.telegram_alias is None

    def test_display_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(display_name='a' * 26)

    def test_empty_display_name(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(display_name='')

    def test_invalid_gender(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(gender='X')

    def test_country_too_short(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(country='K')

    def test_country_too_long(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(country='KAZ')

    def test_country_must_contain_uppercase_letters(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(country='kz')

    def test_country_must_contain_only_letters(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(country='12')

    def test_bio_too_long(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(bio='a' * 76)

    def test_empty_bio(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(bio='')

    def test_telegram_alias_too_short(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(telegram_alias='test')

    def test_telegram_alias_too_long(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(telegram_alias='a' * 33)

    def test_telegram_alias_must_start_with_letter(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(telegram_alias='1test_user')

    def test_telegram_alias_invalid_characters(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateRequest(telegram_alias='test-user')

    def test_birth_date_too_recent(self) -> None:
        birthday = date.today() - timedelta(days=365 * 5)

        with pytest.raises(ValidationError):
            UserUpdateRequest(birth_date=birthday)

    def test_birth_date_too_old(self) -> None:
        birthday = date.today() - timedelta(days=365 * 101)

        with pytest.raises(ValidationError):
            UserUpdateRequest(birth_date=birthday)

    def test_birth_date_valid(self) -> None:
        birthday = date.today() - timedelta(days=365 * 20)

        data = UserUpdateRequest(birth_date=birthday)

        assert data.birth_date == birthday

    def test_birth_date_in_future(self) -> None:
        birthday = date.today() + timedelta(days=1)

        with pytest.raises(ValidationError):
            UserUpdateRequest(birth_date=birthday)


class TestUserUpdateResponse:
    def test_valid_data(self) -> None:
        data = UserUpdateResponse(
            email='user@example.com',
            display_name='Test User',
            gender=Gender.MALE,
            country='KZ',
            birth_date=date(2000, 1, 1),
            bio='Test bio',
            telegram_alias='test_user',
        )

        assert data.email == 'user@example.com'
        assert data.display_name == 'Test User'
        assert data.gender == Gender.MALE
        assert data.country == 'KZ'
        assert data.birth_date == date(2000, 1, 1)
        assert data.bio == 'Test bio'
        assert data.telegram_alias == 'test_user'

    def test_nullable_fields(self) -> None:
        data = UserUpdateResponse(
            email='user@example.com',
            display_name=None,
            gender=None,
            country=None,
            birth_date=None,
            bio=None,
            telegram_alias=None,
        )

        assert data.display_name is None
        assert data.gender is None
        assert data.country is None
        assert data.birth_date is None
        assert data.bio is None
        assert data.telegram_alias is None

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdateResponse(
                email='not-an-email',
                display_name='Test User',
                gender=Gender.MALE,
                country='KZ',
                birth_date=date(2000, 1, 1),
                bio='Test bio',
                telegram_alias='test_user',
            )

    def test_from_attributes(self) -> None:
        class UserModel:
            email = 'user@example.com'
            display_name = 'Test User'
            gender = Gender.MALE
            country = 'KZ'
            birth_date = date(2000, 1, 1)
            bio = 'Test bio'
            telegram_alias = 'test_user'

        data = UserUpdateResponse.model_validate(
            UserModel(),
            from_attributes=True,
        )

        assert data.email == UserModel.email
        assert data.display_name == UserModel.display_name
        assert data.gender == UserModel.gender
        assert data.country == UserModel.country
        assert data.birth_date == UserModel.birth_date
        assert data.bio == UserModel.bio
        assert data.telegram_alias == UserModel.telegram_alias


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


class TestEmailChangeRequest:
    def test_valid_data(self) -> None:
        data = EmailChangeRequest(
            new_email='new@example.com',
            password='password123',
        )

        assert data.new_email == 'new@example.com'
        assert data.password == 'password123'

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            EmailChangeRequest(
                new_email='not-an-email',
                password='password123',
            )

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            EmailChangeRequest(
                new_email='new@example.com',
                password='short',
            )

    def test_password_too_long(self) -> None:
        password = 'a' * 129

        with pytest.raises(ValidationError):
            EmailChangeRequest(
                new_email='new@example.com',
                password=password,
            )


class TestEmailChangeConfirm:
    def test_valid_code(self) -> None:
        data = EmailChangeConfirm(code='123456')

        assert data.code == '123456'

    def test_code_too_short(self) -> None:
        with pytest.raises(ValidationError):
            EmailChangeConfirm(code='12345')

    def test_code_too_long(self) -> None:
        with pytest.raises(ValidationError):
            EmailChangeConfirm(code='1234567')

    def test_code_must_contain_only_digits(self) -> None:
        with pytest.raises(ValidationError):
            EmailChangeConfirm(code='12345a')

    def test_code_must_not_contain_spaces(self) -> None:
        with pytest.raises(ValidationError):
            EmailChangeConfirm(code='123 56')
