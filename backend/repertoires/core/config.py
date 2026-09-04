from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class DatabaseSettings(BaseModel):
    url: str


class JwtSettings(BaseModel):
    public_key_path: Path = Path('keys/public_key.pem')


class Settings(BaseSettings):
    """Settings for the server."""

    database: DatabaseSettings
    jwt: JwtSettings = JwtSettings()

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore',
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
