from functools import lru_cache
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class RefreshTokenCookieConfig(BaseModel):
    name: str = 'refresh_token'
    secure: bool = True
    path: str = '/api/v1/auth/'
    httponly: bool = True
    samesite: Literal['lax', 'strict', 'none'] = 'strict'


class Settings(BaseSettings):
    """Settings for the server."""

    database_url: str

    # 3 minutes and 30 days for access and refresh tokens respectively
    access_token_expire_seconds: int = 3 * 60
    refresh_token_expire_seconds: int = 60 * 60 * 24 * 30

    refresh_token_cookie: RefreshTokenCookieConfig = RefreshTokenCookieConfig()

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
