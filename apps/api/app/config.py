from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List
import os
import json
import logging

logger = logging.getLogger(__name__)

DEFAULT_JWT_SECRET = "your-super-secret-jwt-key-change-in-production"

# create_async_engine refuses a synchronous driver. Hosted Postgres providers hand out
# "postgresql://..." and every SQLAlchemy tutorial uses "sqlite:///...", so accept the
# conventional spellings and map them onto the async drivers this app actually uses.
_ASYNC_DRIVERS = {
    "sqlite": "aiosqlite",
    "postgresql": "asyncpg",
    "postgres": "asyncpg",
}


def _to_async_url(url: str) -> str:
    scheme, separator, remainder = url.partition("://")
    if not separator:
        return url
    base, plus, driver = scheme.partition("+")
    if plus:
        return url
    async_driver = _ASYNC_DRIVERS.get(base)
    if not async_driver:
        return url
    return f"{base}+{async_driver}://{remainder}"


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./app.db"

    @field_validator("database_url")
    @classmethod
    def ensure_async_driver(cls, v):
        return _to_async_url(v)

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    # AI Providers
    openai_api_key: str = ""

    # Voice Providers
    elevenlabs_api_key: str = ""
    # Voice used for narration when synthesizing. ElevenLabs requires an explicit
    # voice_id, so this is what the pipeline renders with.
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"

    # Video Providers
    runway_api_key: str = ""
    higgsfield_api_key: str = ""
    higgsfield_video_model: str = ""

    # Storage
    storage_backend: str = "local"  # local | s3
    storage_dir: str = "./storage"
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "ai-video-platform"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"

    # Render
    render_async: bool = False

    # Quality gate
    qa_threshold: int = 70

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()

if settings.jwt_secret == DEFAULT_JWT_SECRET:
    logger.warning(
        "JWT_SECRET is using the built-in development default. "
        "Set JWT_SECRET before exposing this deployment; tokens are forgeable until you do."
    )
