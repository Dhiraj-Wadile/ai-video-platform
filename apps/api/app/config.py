from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os
import json


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./test.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = "your-super-secret-jwt-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 1440

    # AI Providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # Voice Providers
    elevenlabs_api_key: str = ""
    edge_tts_voice: str = "en-US-AriaNeural"

    # Image Providers
    pollinations_enabled: bool = True

    # Video Providers
    runway_api_key: str = ""

    # Storage
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "ai-video-platform"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"

    # App
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Cost Management
    max_monthly_cost_cents: int = 50000
    default_quality: str = "balanced"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
