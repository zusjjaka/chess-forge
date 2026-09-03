import secrets
import uuid
from datetime import (
    UTC,
    datetime,
)
from typing import Any

import jwt

from core.config import get_settings
from core.jwt import (
    PRIVATE_KEY,
    PUBLIC_KEY,
)

settings = get_settings()


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    expires_at = now + settings.access_token_lifetime

    payload = {
        'sub': str(user_id),
        'iat': now,
        'exp': expires_at,
        'jti': str(uuid.uuid4()),
    }

    return jwt.encode(
        payload,
        PRIVATE_KEY,
        algorithm='RS256',
    )


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        PUBLIC_KEY,
        algorithms=['RS256'],
    )


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def generate_verification_code() -> str:
    secret_code: int = secrets.randbelow(1_000_000)
    return f'{secret_code:06d}'
