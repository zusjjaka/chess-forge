from datetime import timedelta
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class DatabaseSettings(BaseModel):
    url: str


class RabbitmqSettings(BaseModel):
    url: str
    queue: str = 'email_queue'


class RefreshTokenCookieConfig(BaseModel):
    name: str = 'refresh_token'
    secure: bool = True
    path: str = '/api/v1/auth/'
    httponly: bool = True
    samesite: Literal['lax', 'strict', 'none'] = 'strict'


class Settings(BaseSettings):
    """Settings for the server."""

    database: DatabaseSettings
    rabbitmq: RabbitmqSettings

    refresh_token_cookie: RefreshTokenCookieConfig = RefreshTokenCookieConfig()

    access_token_lifetime: timedelta = timedelta(minutes=3)
    refresh_token_lifetime: timedelta = timedelta(days=30)
    verification_code_lifetime: timedelta = timedelta(minutes=15)

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore',
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
