from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class DatabaseSettings(BaseModel):
    url: str


class Settings(BaseSettings):
    """Settings for the server."""

    database: DatabaseSettings

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore',
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
