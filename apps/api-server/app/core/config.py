from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", enable_decoding=False)
    app_env: str = "development"
    app_name: str = "Zhongcheng SCM Platform"
    database_url: str
    auth_jwt_secret: SecretStr
    auth_access_token_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:5173"]
    task_mode: str = "inline"
    storage_mode: str = "local"
    local_storage_path: Path = Path("local-data/files")
    redis_enabled: bool = False
    minio_enabled: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        return (
            [x.strip() for x in value.split(",") if x.strip()] if isinstance(value, str) else value
        )

    @field_validator("local_storage_path", mode="before")
    @classmethod
    def resolve_local_storage_path(cls, value: str | Path) -> Path:
        path = Path(value)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @field_validator("auth_access_token_minutes")
    @classmethod
    def positive_access_token_minutes(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("auth_access_token_minutes must be positive")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
