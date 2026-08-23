import uuid

import jwt
from db.session import get_db_session
from exceptions import InvalidAccessTokenError
from fastapi import (
    Depends,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from models.user import User
from repositories.users import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession
from utils.tokens import decode_access_token

bearer_scheme = HTTPBearer()


async def get_current_user(
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
