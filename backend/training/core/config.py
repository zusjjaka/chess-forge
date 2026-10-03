from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    url: str


class RepertoireServiceSettings(BaseModel):
    host: str
    port: int
    timeout: float


class JwtSettings(BaseModel):
    public_key_path: Path = Path('keys/public_key.pem')


class Settings(BaseSettings):
    database: DatabaseSettings
    repertoire_service: RepertoireServiceSettings
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
