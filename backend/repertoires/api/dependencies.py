import uuid

import jwt
from fastapi import (
    Depends,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db_session
from exceptions import InvalidAccessTokenError
from services.line import LineService
from services.repertoire import RepertoireService
from utils.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
        ) -> uuid.UUID:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload['sub']))
    except (ValueError, KeyError, jwt.InvalidTokenError):
        raise InvalidAccessTokenError from None

    return user_id


def get_repertoire_service(
        session: AsyncSession = Depends(get_db_session)
        ) -> RepertoireService:
    return RepertoireService(session)


def get_line_service(
        session: AsyncSession = Depends(get_db_session)
        ) -> LineService:
    return LineService(session)
