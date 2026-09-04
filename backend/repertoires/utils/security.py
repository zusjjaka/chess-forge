from pathlib import Path

import jwt

from core.config import get_settings

settings = get_settings()


def load_public_key(path: Path) -> str:
    return path.read_text(encoding='utf-8')


PUBLIC_KEY = load_public_key(settings.jwt.public_key_path)


def decode_access_token(token: str) -> dict[str, object]:
    return jwt.decode(
        token,
        PUBLIC_KEY,
        algorithms=['RS256'],
    )
