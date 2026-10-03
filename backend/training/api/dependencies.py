import uuid
from typing import cast

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
from exceptions import InvalidAccessTokenError
from grpc_client.client import RepertoireGrpcClient
from services.training import TrainingService
from utils.security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_user_id(
        credentials: HTTPAuthorizationCredentials = Depends(
            bearer_scheme,
        ),
        ) -> uuid.UUID:

    try:
        payload = decode_access_token(
            credentials.credentials,
        )

        user_id = uuid.UUID(
            str(payload['sub']),
        )

    except (
        ValueError,
        KeyError,
        jwt.InvalidTokenError,
    ):
        raise InvalidAccessTokenError from None

    return user_id


def get_repertoire_client(
        request: Request,
        ) -> RepertoireGrpcClient:

    return cast(
        RepertoireGrpcClient,
        request.app.state.repertoire_client,
    )


def get_training_service(
        session: AsyncSession = Depends(
            get_db_session,
        ),
        repertoire_client: RepertoireGrpcClient = Depends(
            get_repertoire_client,
        ),
        ) -> TrainingService:

    return TrainingService(
        session=session,
        repertoire_client=repertoire_client,
    )
