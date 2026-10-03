from pathlib import Path

import jwt

from core.config import get_settings

settings = get_settings()

PUBLIC_KEY = Path(
    settings.jwt.public_key_path,
).read_text(
    encoding='utf-8',
)


def decode_access_token(token: str) -> dict[str, object]:
    return jwt.decode(
        token,
        PUBLIC_KEY,
        algorithms=['RS256'],
    )
