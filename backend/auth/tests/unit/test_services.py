from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from exceptions import (
    EmailSameError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    PasswordInvalidError,
    RefreshTokenExpiredError,
    RefreshTokenInvalidError,
    RefreshTokenReuseError,
    UserAlreadyExistError,
    VerificationCodeInvalidError,
)
from models.refresh_token import RefreshToken
from models.user import User
from models.verification_code import (
    EmailChangeCode,
    EmailVerificationCode,
    PasswordResetCode,
)
from services.verification_code import (
    EmailChangeService,
    EmailVerificationService,
    PasswordResetService,
)
from publishers.email import EmailPublisher
from services.auth import AuthService
from utils.security import (
    verify_password,
    hash_password,
)
from core.config import get_settings


settings = get_settings()


@pytest.fixture
def email_change_service(
    session: AsyncMock,
) -> EmailChangeService:
    return EmailChangeService(session=session)


@pytest.fixture
def password_reset_service(
    session: AsyncMock,
) -> PasswordResetService:
    return PasswordResetService(session=session)


@pytest.fixture
def email_verification_service(
    session: AsyncMock,
) -> EmailVerificationService:
    return EmailVerificationService(session=session)


@pytest.fixture
def email_publisher() -> AsyncMock:
    return AsyncMock(spec=EmailPublisher)


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
def service(
    session: AsyncMock,
    email_publisher: AsyncMock,
) -> AuthService:
    return AuthService(
        session=session,
        email_publisher=email_publisher,
    )


@pytest.fixture
def verification_service(
    session: AsyncMock,
) -> EmailVerificationService:
    return EmailVerificationService(session=session)


@pytest.mark.asyncio
async def test_register_creates_user(
    service: AuthService,
    user: User,
) -> None:
    verification_code = type(
        'VerificationCode',
        (),
        {'id': uuid4()},
    )()

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
        patch(
            'services.auth.generate_verification_code',
            return_value='123456',
        ),
        patch.object(
            service.email_codes,
            'create',
            new_callable=AsyncMock,
            return_value=verification_code,
        ) as create_verification_code,
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

    create_verification_code.assert_awaited_once()

    service.session.commit.assert_awaited_once()

    service.email_publisher.publish_email_verification.assert_awaited_once_with(
        email=user.email,
        code='123456',
        message_id=verification_code.id,
    )


@pytest.mark.asyncio
async def test_register_rejects_existing_verified_user(
    service: AuthService,
    user: User,
) -> None:
    user.is_email_verified = True

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

    service.email_publisher.publish_email_verification.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_updates_existing_unverified_user(
    service: AuthService,
    user: User,
) -> None:
    user.is_email_verified = False

    verification_code = type(
        'VerificationCode',
        (),
        {'id': uuid4()},
    )()

    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch(
            'services.auth.hash_password',
            return_value='new-hashed-password',
        ) as hash_password,
        patch(
            'services.auth.generate_verification_code',
            return_value='654321',
        ),
        patch.object(
            service.email_codes,
            'create',
            new_callable=AsyncMock,
            return_value=verification_code,
        ) as create_verification_code,
    ):
        result = await service.register(
            email='user@example.com',
            password='new-password',
        )

    assert result is user
    assert user.password_hash == 'new-hashed-password'

    hash_password.assert_called_once_with('new-password')

    create_verification_code.assert_awaited_once()

    service.session.commit.assert_awaited_once()

    service.email_publisher.publish_email_verification.assert_awaited_once_with(
        email=user.email,
        code='654321',
        message_id=verification_code.id,
    )


@pytest.mark.asyncio
async def test_register_hashes_password(
    service: AuthService,
    user: User,
) -> None:
    verification_code = type(
        'VerificationCode',
        (),
        {'id': uuid4()},
    )()

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
        patch.object(
            service.email_codes,
            'create',
            new_callable=AsyncMock,
            return_value=verification_code,
        ),
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
            'services.auth.hash_secret',
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
        pytest.raises(InvalidCredentialsError),
    ):
        await service.login(
            email='unknown@example.com',
            password='password123',
            ip_addr=None,
            user_agent=None,
        )

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
        pytest.raises(InvalidCredentialsError),
    ):
        await service.login(
            email='user@example.com',
            password='wrong-password',
            ip_addr=None,
            user_agent=None,
        )

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
            'services.auth.hash_secret',
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
        ) as create_token,
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

    create_token.assert_awaited_once()

    call_kwargs = create_token.await_args.kwargs

    assert call_kwargs['user_id'] == user_id
    assert call_kwargs['token_hash'] == b'old-hash'
    assert call_kwargs['family_id'] == family_id
    assert call_kwargs['ip_addr'] == '127.0.0.1'
    assert call_kwargs['user_agent'] == 'pytest'

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
            'services.auth.hash_secret',
            return_value=b'unknown-hash',
        ),
        patch.object(
            service.refresh_tokens,
            'get_by_hash',
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(RefreshTokenInvalidError),
    ):
        await service.refresh(
            refresh_token='unknown-token',
            ip_addr=None,
            user_agent=None,
        )

    service.session.commit.assert_not_awaited()


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
            'services.auth.hash_secret',
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
        pytest.raises(RefreshTokenReuseError),
    ):
        await service.refresh(
            refresh_token='reused-token',
            ip_addr=None,
            user_agent=None,
        )

    revoke_family.assert_awaited_once_with(
        stored_token.family_id,
    )

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
            'services.auth.hash_secret',
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
        pytest.raises(RefreshTokenExpiredError),
    ):
        await service.refresh(
            refresh_token='expired-token',
            ip_addr=None,
            user_agent=None,
        )

    revoke.assert_awaited_once_with(stored_token)

    service.session.commit.assert_awaited_once()


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
            'services.auth.hash_secret',
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
            'services.auth.hash_secret',
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


@pytest.mark.asyncio
async def test_verify_confirms_user_email(
    verification_service: EmailVerificationService,
    user: User,
) -> None:
    verification_code = type(
        'VerificationCode',
        (),
        {'id': uuid4()},
    )()

    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ) as hash_secret,
        patch.object(
            verification_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=verification_code,
        ) as get_valid_code,
        patch.object(
            verification_service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch.object(
            verification_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
    ):
        await verification_service.verify(
            user_id=user.id,
            code='123456',
        )

    hash_secret.assert_called_once_with('123456')

    get_valid_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'code-hash',
    )

    get_user.assert_awaited_once_with(user.id)

    assert user.is_email_verified is True

    mark_as_used.assert_awaited_once_with(
        verification_code.id,
    )

    verification_service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_rejects_invalid_code(
    verification_service: EmailVerificationService,
    user: User,
) -> None:
    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'wrong-code-hash',
        ),
        patch.object(
            verification_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_valid_code,
        patch.object(
            verification_service.users,
            'get_by_id',
            new_callable=AsyncMock,
        ) as get_user,
        patch.object(
            verification_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
        pytest.raises(VerificationCodeInvalidError),
    ):
        await verification_service.verify(
            user_id=user.id,
            code='wrong-code',
        )

    get_valid_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'wrong-code-hash',
    )

    get_user.assert_not_awaited()
    mark_as_used.assert_not_awaited()

    verification_service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_rejects_missing_user(
    verification_service: EmailVerificationService,
    user: User,
) -> None:
    verification_code = type(
        'VerificationCode',
        (),
        {'id': uuid4()},
    )()

    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ),
        patch.object(
            verification_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=verification_code,
        ),
        patch.object(
            verification_service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_user,
        patch.object(
            verification_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
        pytest.raises(VerificationCodeInvalidError),
    ):
        await verification_service.verify(
            user_id=user.id,
            code='123456',
        )

    get_user.assert_awaited_once_with(user.id)

    mark_as_used.assert_not_awaited()

    verification_service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_password_reset(
    service: AuthService,
    user: User,
) -> None:
    reset_code = type(
        'PasswordResetCode',
        (),
        {'id': uuid4()},
    )()

    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch(
            'services.auth.generate_verification_code',
            return_value='123456',
        ) as generate_code,
        patch(
            'services.auth.hash_secret',
            return_value=b'code-hash',
        ) as hash_secret,
        patch.object(
            service.passw_codes,
            'create',
            new_callable=AsyncMock,
            return_value=reset_code,
        ) as create_code,
    ):
        await service.request_password_reset(
            email=user.email,
        )

    get_user.assert_awaited_once_with(user.email)
    generate_code.assert_called_once()
    hash_secret.assert_called_once_with('123456')

    create_code.assert_awaited_once()

    call_kwargs = create_code.await_args.kwargs

    assert call_kwargs['user_id'] == user.id
    assert call_kwargs['code_hash'] == b'code-hash'
    assert call_kwargs['expires_at'] > datetime.now(UTC)

    service.session.commit.assert_awaited_once()

    service.email_publisher.publish_password_reset.assert_awaited_once_with(
        email=user.email,
        code='123456',
        message_id=reset_code.id,
    )


@pytest.mark.asyncio
async def test_request_password_reset_does_nothing_for_unknown_user(
    service: AuthService,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_user,
        patch(
            'services.auth.generate_verification_code',
        ) as generate_code,
        patch.object(
            service.passw_codes,
            'create',
            new_callable=AsyncMock,
        ) as create_code,
    ):
        await service.request_password_reset(
            email='unknown@example.com',
        )

    get_user.assert_awaited_once_with('unknown@example.com')
    generate_code.assert_not_called()
    create_code.assert_not_awaited()

    service.session.commit.assert_not_awaited()
    service.email_publisher.publish_password_reset.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_reset(
    password_reset_service: PasswordResetService,
    user: User,
) -> None:
    reset_code = type(
        'PasswordResetCode',
        (),
        {'id': uuid4()},
    )()

    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ) as hash_secret,
        patch(
            'services.verification_code.hash_password',
            return_value='new-password-hash',
        ) as hash_password,
        patch.object(
            password_reset_service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch.object(
            password_reset_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=reset_code,
        ) as get_code,
        patch.object(
            password_reset_service.refresh_tokens,
            'revoke_all_for_user',
            new_callable=AsyncMock,
        ) as revoke_all,
        patch.object(
            password_reset_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
    ):
        await password_reset_service.reset(
            email=user.email,
            code='123456',
            password='new-password',
        )

    hash_secret.assert_called_once_with('123456')
    get_user.assert_awaited_once_with(user.email)

    get_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'code-hash',
    )

    hash_password.assert_called_once_with('new-password')

    assert user.password_hash == 'new-password-hash'

    revoke_all.assert_awaited_once_with(user.id)
    mark_as_used.assert_awaited_once_with(reset_code.id)

    password_reset_service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_password_reset_rejects_unknown_user(
    password_reset_service: PasswordResetService,
) -> None:
    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ),
        patch.object(
            password_reset_service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            password_reset_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
        ) as get_code,
        patch.object(
            password_reset_service.refresh_tokens,
            'revoke_all_for_user',
            new_callable=AsyncMock,
        ) as revoke_all,
        patch.object(
            password_reset_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
        patch(
            'services.verification_code.hash_password',
        ) as hash_password,
        pytest.raises(VerificationCodeInvalidError),
    ):
        await password_reset_service.reset(
            email='unknown@example.com',
            code='123456',
            password='new-password',
        )

    hash_password.assert_not_called()
    get_code.assert_not_awaited()
    revoke_all.assert_not_awaited()
    mark_as_used.assert_not_awaited()

    password_reset_service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_password_reset_rejects_invalid_code(
    password_reset_service: PasswordResetService,
    user: User,
) -> None:
    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'wrong-code-hash',
        ) as hash_secret,
        patch.object(
            password_reset_service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=user,
        ),
        patch.object(
            password_reset_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_code,
        patch(
            'services.verification_code.hash_password',
        ) as hash_password,
        patch.object(
            password_reset_service.refresh_tokens,
            'revoke_all_for_user',
            new_callable=AsyncMock,
        ) as revoke_all,
        patch.object(
            password_reset_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
        pytest.raises(VerificationCodeInvalidError),
    ):
        await password_reset_service.reset(
            email=user.email,
            code='wrong-code',
            password='new-password',
        )

    hash_secret.assert_called_once_with('wrong-code')

    get_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'wrong-code-hash',
    )

    hash_password.assert_not_called()
    revoke_all.assert_not_awaited()
    mark_as_used.assert_not_awaited()

    password_reset_service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_email(
    verification_service: EmailVerificationService,
    user: User,
) -> None:
    verification_code = type(
        'EmailVerificationCode',
        (),
        {'id': uuid4()},
    )()

    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ) as hash_secret,
        patch.object(
            verification_service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch.object(
            verification_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=verification_code,
        ) as get_code,
        patch.object(
            verification_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
    ):
        await verification_service.verify(
            user_id=user.id,
            code='123456',
        )

    hash_secret.assert_called_once_with('123456')

    get_user.assert_awaited_once_with(user.id)

    get_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'code-hash',
    )

    assert user.is_email_verified is True

    mark_as_used.assert_awaited_once_with(
        verification_code.id,
    )

    verification_service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_email_rejects_unknown_user(
    verification_service: EmailVerificationService,
) -> None:
    verification_code = type(
        'EmailVerificationCode',
        (),
        {'id': uuid4()},
    )()

    user_id = uuid4()

    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ),
        patch.object(
            verification_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=verification_code,
        ) as get_code,
        patch.object(
            verification_service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_user,
        patch.object(
            verification_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
        pytest.raises(VerificationCodeInvalidError),
    ):
        await verification_service.verify(
            user_id=user_id,
            code='123456',
        )

    get_code.assert_awaited_once_with(
        user_id=user_id,
        code_hash=b'code-hash',
    )

    get_user.assert_awaited_once_with(user_id)

    mark_as_used.assert_not_awaited()

    verification_service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_email_rejects_invalid_code(
    verification_service: EmailVerificationService,
    user: User,
) -> None:
    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'wrong-code-hash',
        ) as hash_secret,
        patch.object(
            verification_service.users,
            'get_by_id',
            new_callable=AsyncMock
        ) as get_user,
        patch.object(
            verification_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_code,
        patch.object(
            verification_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
        pytest.raises(VerificationCodeInvalidError),
    ):
        await verification_service.verify(
            user_id=user.id,
            code='wrong-code',
        )

    hash_secret.assert_called_once_with('wrong-code')

    get_user.assert_not_awaited()

    get_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'wrong-code-hash',
    )

    mark_as_used.assert_not_awaited()

    verification_service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_user_password(
    service: AuthService,
    user: User,
) -> None:
    current_password = 'current-password'
    new_password = 'new-password'

    user.password_hash = hash_password(current_password)

    service.users.get_by_id = AsyncMock(return_value=user)
    service.session.commit = AsyncMock()

    await service.change_user_password(
        user_id=user.id,
        current_password=current_password,
        new_password=new_password,
    )

    assert verify_password(new_password, user.password_hash)
    assert not verify_password(current_password, user.password_hash)

    service.users.get_by_id.assert_awaited_once_with(user.id)
    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_user_password_user_not_found(
    service: AuthService,
    user: User,
) -> None:
    service.users.get_by_id = AsyncMock(return_value=None)
    service.session.commit = AsyncMock()

    with pytest.raises(PasswordInvalidError):
        await service.change_user_password(
            user_id=user.id,
            current_password='current-password',
            new_password='new-password',
        )

    service.users.get_by_id.assert_awaited_once_with(user.id)
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_user_password_invalid_current_password(
    service: AuthService,
    user: User,
) -> None:
    user.password_hash = hash_password('correct-password')

    service.users.get_by_id = AsyncMock(return_value=user)
    service.session.commit = AsyncMock()

    with pytest.raises(PasswordInvalidError):
        await service.change_user_password(
            user_id=user.id,
            current_password='wrong-password',
            new_password='new-password',
        )

    assert verify_password('correct-password', user.password_hash)

    service.users.get_by_id.assert_awaited_once_with(user.id)
    service.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_email_change(
    service: AuthService,
    user: User,
) -> None:
    new_email = 'new@example.com'
    message_id = uuid4()
    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    with (
        patch.object(
            service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_by_email,
        patch(
            'services.auth.verify_password',
            return_value=True,
        ) as verify_password_mock,
        patch(
            'services.auth.generate_verification_code',
            return_value='123456',
        ) as generate_code,
        patch(
            'services.auth.hash_secret',
            return_value=b'code-hash',
        ) as hash_secret_mock,
        patch.object(
            service.email_change_codes,
            'create',
            new_callable=AsyncMock,
        ) as create_code,
    ):
        create_code.return_value = type(
            'EmailChangeCode',
            (),
            {'id': message_id},
        )()

        await service.request_email_change(
            user_id=user.id,
            new_email=new_email,
            password='password123',
        )

    get_user.assert_awaited_once_with(user.id)
    verify_password_mock.assert_called_once_with(
        'password123',
        user.password_hash,
    )
    get_by_email.assert_awaited_once_with(new_email)
    generate_code.assert_called_once()
    hash_secret_mock.assert_called_once_with('123456')

    create_code.assert_awaited_once()

    kwargs = create_code.await_args.kwargs

    assert kwargs['user_id'] == user.id
    assert kwargs['new_email'] == new_email
    assert kwargs['code_hash'] == b'code-hash'
    assert datetime.now(UTC) < kwargs['expires_at']
    assert kwargs['expires_at'] <= (
        datetime.now(UTC) + settings.verification_code_lifetime
    )

    service.session.commit.assert_awaited_once()

    service.email_publisher.publish_email_change.assert_awaited_once_with(
        email=new_email,
        code='123456',
        message_id=message_id,
    )


@pytest.mark.asyncio
async def test_request_email_change_user_not_found(
    service: AuthService,
) -> None:
    user_id = uuid4()

    with patch.object(
        service.users,
        'get_by_id',
        new_callable=AsyncMock,
        return_value=None,
    ) as get_user:
        with pytest.raises(PasswordInvalidError):
            await service.request_email_change(
                user_id=user_id,
                new_email='new@example.com',
                password='password123',
            )

    get_user.assert_awaited_once_with(user_id)
    service.session.commit.assert_not_awaited()
    service.email_publisher.publish_email_change.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_email_change_invalid_password(
    service: AuthService,
    user: User,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch(
            'services.auth.verify_password',
            return_value=False,
        ) as verify_password_mock,
    ):
        with pytest.raises(PasswordInvalidError):
            await service.request_email_change(
                user_id=user.id,
                new_email='new@example.com',
                password='wrong-password',
            )

    get_user.assert_awaited_once_with(user.id)
    verify_password_mock.assert_called_once_with(
        'wrong-password',
        user.password_hash,
    )
    service.session.commit.assert_not_awaited()
    service.email_publisher.publish_email_change.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_email_change_same_email(
    service: AuthService,
    user: User,
) -> None:
    with (
        patch.object(
            service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch(
            'services.auth.verify_password',
            return_value=True,
        ) as verify_password_mock,
    ):
        with pytest.raises(EmailSameError):
            await service.request_email_change(
                user_id=user.id,
                new_email=user.email,
                password='password123',
            )

    get_user.assert_awaited_once_with(user.id)
    verify_password_mock.assert_called_once_with(
        'password123',
        user.password_hash,
    )
    service.session.commit.assert_not_awaited()
    service.email_publisher.publish_email_change.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_email_change_email_already_exists(
    service: AuthService,
    user: User,
) -> None:
    existing_user = User(
        id=uuid4(),
        email='new@example.com',
        password_hash='hashed-password',
    )

    with (
        patch.object(
            service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch(
            'services.auth.verify_password',
            return_value=True,
        ) as verify_password_mock,
        patch.object(
            service.users,
            'get_by_email',
            new_callable=AsyncMock,
            return_value=existing_user,
        ) as get_by_email,
    ):
        with pytest.raises(UserAlreadyExistError):
            await service.request_email_change(
                user_id=user.id,
                new_email='new@example.com',
                password='password123',
            )

    get_user.assert_awaited_once_with(user.id)
    verify_password_mock.assert_called_once_with(
        'password123',
        user.password_hash,
    )
    get_by_email.assert_awaited_once_with('new@example.com')
    service.session.commit.assert_not_awaited()
    service.email_publisher.publish_email_change.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_email_change(
    email_change_service: EmailChangeService,
    user: User,
) -> None:
    new_email = 'new@example.com'
    code_id = uuid4()

    email_change_code = EmailChangeCode(
        id=code_id,
        user_id=user.id,
        new_email=new_email,
        code_hash=b'code-hash',
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ) as hash_secret_mock,
        patch.object(
            email_change_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=email_change_code,
        ) as get_code,
        patch.object(
            email_change_service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch.object(
            email_change_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
    ):
        await email_change_service.confirm(
            user_id=user.id,
            code='123456',
        )

    hash_secret_mock.assert_called_once_with('123456')

    get_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'code-hash',
    )

    get_user.assert_awaited_once_with(user.id)

    assert user.email == new_email
    assert user.is_email_verified is True

    mark_as_used.assert_awaited_once_with(code_id)
    email_change_service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_email_change_invalid_code(
    email_change_service: EmailChangeService,
    user: User,
) -> None:
    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ) as hash_secret_mock,
        patch.object(
            email_change_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_code,
        patch.object(
            email_change_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
    ):
        with pytest.raises(VerificationCodeInvalidError):
            await email_change_service.confirm(
                user_id=user.id,
                code='123456',
            )

    hash_secret_mock.assert_called_once_with('123456')

    get_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'code-hash',
    )

    email_change_service.session.commit.assert_not_awaited()
    mark_as_used.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_email_change_user_not_found(
    email_change_service: EmailChangeService,
    user: User,
) -> None:
    email_change_code = EmailChangeCode(
        id=uuid4(),
        user_id=user.id,
        new_email='new@example.com',
        code_hash=b'code-hash',
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    with (
        patch(
            'services.verification_code.hash_secret',
            return_value=b'code-hash',
        ),
        patch.object(
            email_change_service.codes,
            'get_valid_by_user_id',
            new_callable=AsyncMock,
            return_value=email_change_code,
        ) as get_code,
        patch.object(
            email_change_service.codes,
            'mark_as_used',
            new_callable=AsyncMock,
        ) as mark_as_used,
        patch.object(
            email_change_service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_user,
    ):
        with pytest.raises(VerificationCodeInvalidError):
            await email_change_service.confirm(
                user_id=user.id,
                code='123456',
            )

    get_code.assert_awaited_once_with(
        user_id=user.id,
        code_hash=b'code-hash',
    )

    get_user.assert_awaited_once_with(user.id)

    email_change_service.session.commit.assert_not_awaited()
    mark_as_used.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_user(
    service: AuthService,
    user: User,
) -> None:
    data = {
        'display_name': 'New Name',
        'gender': 'M',
        'country': 'KZ',
        'birth_date': datetime.now(UTC).date(),
        'bio': 'New bio',
        'telegram_alias': 'new_user',
    }

    with (
        patch.object(
            service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ) as get_user,
        patch.object(
            service.users,
            'update',
            new_callable=AsyncMock,
            return_value=user,
        ) as update_user,
    ):
        result = await service.update_user(
            user_id=user.id,
            data=data,
        )

    assert result is user

    get_user.assert_awaited_once_with(user.id)

    update_user.assert_awaited_once_with(
        user=user,
        data=data,
    )

    service.session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_user_not_found(
    service: AuthService,
) -> None:
    user_id = uuid4()
    data = {
        'display_name': 'New Name',
    }

    with (
        patch.object(
            service.users,
            'get_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ) as get_user,
        patch.object(
            service.users,
            'update',
            new_callable=AsyncMock,
        ) as update_user,
        pytest.raises(InvalidAccessTokenError),
    ):
        await service.update_user(
            user_id=user_id,
            data=data,
        )

    get_user.assert_awaited_once_with(user_id)

    update_user.assert_not_awaited()

    service.session.commit.assert_not_awaited()
