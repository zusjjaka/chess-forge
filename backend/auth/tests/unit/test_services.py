from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from exceptions import (
    InvalidCredentialsError,
    RefreshTokenExpiredError,
    RefreshTokenInvalidError,
    RefreshTokenReuseError,
    UserAlreadyExistError,
    VerificationCodeInvalidError,
)
from models.refresh_token import RefreshToken
from models.user import User
from publishers.email import EmailPublisher
from services.auth import AuthService
from services.verification_code import EmailVerificationService


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
            service.codes,
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
            service.codes,
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
            service.codes,
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
