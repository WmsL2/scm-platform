from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", enable_decoding=False)
    app_env: str = "development"
    app_name: str = "Zhongcheng SCM Platform"
    database_url: str
    auth_jwt_secret: SecretStr
    auth_access_token_minutes: int = 30
    auth_refresh_idle_days: int = 3
    auth_session_absolute_days: int = 30
    auth_refresh_rotation_grace_seconds: int = 30
    auth_refresh_cookie_secure: bool | None = None
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

    @field_validator(
        "auth_access_token_minutes",
        "auth_refresh_idle_days",
        "auth_session_absolute_days",
        "auth_refresh_rotation_grace_seconds",
    )
    @classmethod
    def positive_auth_duration(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("authentication durations must be positive")
        return value

    @model_validator(mode="after")
    def validate_session_durations(self) -> "Settings":
        if self.auth_refresh_idle_days > self.auth_session_absolute_days:
            raise ValueError(
                "auth_refresh_idle_days cannot exceed auth_session_absolute_days"
            )
        return self

    @property
    def use_secure_refresh_cookie(self) -> bool:
        if self.auth_refresh_cookie_secure is not None:
            return self.auth_refresh_cookie_secure
        return self.app_env.lower() not in {"development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
