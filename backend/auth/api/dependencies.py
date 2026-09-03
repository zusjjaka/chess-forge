import typing
import uuid

import jwt
from fastapi import (
    Depends,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db_session
from exceptions import (
    EmailNotConfirmedError,
    InvalidAccessTokenError,
)
from models.user import User
from publishers.email import EmailPublisher
from repositories.user import UserRepository
from services.auth import AuthService
from services.verification_code import EmailVerificationService
from utils.tokens import decode_access_token

bearer_scheme = HTTPBearer()


async def get_unverified_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload['sub'])
    except (ValueError, KeyError, jwt.InvalidTokenError):
        raise InvalidAccessTokenError from None

    user = await UserRepository(session).get_by_id(user_id)

    if user is None:
        raise InvalidAccessTokenError

    return user


def get_current_user(user: User = Depends(get_unverified_current_user)) -> User:
    if not user.is_email_verified:
        raise EmailNotConfirmedError

    return user


def get_email_publisher(request: Request) -> EmailPublisher:
    email_publisher: typing.Any = request.app.state.email_publisher
    return typing.cast(EmailPublisher, email_publisher)


def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    email_publisher: EmailPublisher = Depends(get_email_publisher),
) -> AuthService:
    return AuthService(session=session, email_publisher=email_publisher)


def get_email_verification_service(
    session: AsyncSession = Depends(get_db_session),
) -> EmailVerificationService:
    return EmailVerificationService(session=session)
