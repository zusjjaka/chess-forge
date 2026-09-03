import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from api.dependencies import (
    get_current_user,
    get_unverified_current_user,
    get_password_reset_service,
    get_email_verification_service,
)
from services.verification_code import (
    PasswordResetService,
    EmailVerificationService,
)
from exceptions import (
    EmailNotConfirmedError,
    InvalidAccessTokenError,
)
from models.user import User


@pytest.fixture
def credentials() -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='valid-token',
    )


@pytest.fixture
def session() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user() -> User:
    return User(
        id=uuid.uuid4(),
        email='user@example.com',
        password_hash='password-hash',
    )


@pytest.mark.asyncio
async def test_get_unverified_current_user_returns_user(
    credentials: HTTPAuthorizationCredentials,
    session: AsyncMock,
    user: User,
) -> None:
    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': str(user.id)},
        ),
        patch(
            'api.dependencies.UserRepository.get_by_id',
            new_callable=AsyncMock,
            return_value=user,
        ),
    ):
        result = await get_unverified_current_user(
            credentials,
            session,
        )

    assert result is user


@pytest.mark.asyncio
async def test_get_unverified_current_user_invalid_token(
    credentials: HTTPAuthorizationCredentials,
    session: AsyncMock,
) -> None:
    with (
        patch(
            'api.dependencies.decode_access_token',
            side_effect=ValueError,
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_unverified_current_user(
            credentials,
            session,
        )


@pytest.mark.asyncio
async def test_get_unverified_current_user_missing_sub(
    credentials: HTTPAuthorizationCredentials,
    session: AsyncMock,
) -> None:
    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={},
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_unverified_current_user(
            credentials,
            session,
        )


@pytest.mark.asyncio
async def test_get_unverified_current_user_invalid_user_id(
    credentials: HTTPAuthorizationCredentials,
    session: AsyncMock,
) -> None:
    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': 'not-a-uuid'},
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_unverified_current_user(
            credentials,
            session,
        )


@pytest.mark.asyncio
async def test_get_unverified_current_user_user_not_found(
    credentials: HTTPAuthorizationCredentials,
    session: AsyncMock,
    user: User,
) -> None:
    with (
        patch(
            'api.dependencies.decode_access_token',
            return_value={'sub': str(user.id)},
        ),
        patch(
            'api.dependencies.UserRepository.get_by_id',
            new_callable=AsyncMock,
            return_value=None,
        ),
        pytest.raises(InvalidAccessTokenError),
    ):
        await get_unverified_current_user(
            credentials,
            session,
        )


@pytest.mark.asyncio
async def test_get_current_user_returns_verified_user(
    user: User,
) -> None:
    user.is_email_verified = True

    result = get_current_user(user)

    assert result is user


@pytest.mark.asyncio
async def test_get_current_user_rejects_unverified_user(
    user: User,
) -> None:
    user.is_email_verified = False

    with pytest.raises(EmailNotConfirmedError):
        await get_current_user(user)


def test_get_password_reset_service(
    session: AsyncMock,
) -> None:
    service = get_password_reset_service(session)

    assert isinstance(service, PasswordResetService)
    assert service.session is session


def test_get_password_reset_service(
    session: AsyncMock,
) -> None:
    service = get_email_verification_service(session)

    assert isinstance(service, EmailVerificationService)
    assert service.session is session
