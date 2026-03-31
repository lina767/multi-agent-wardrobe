from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WARDROBE_", extra="ignore")

    database_url: str = f"sqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'wardrobe.db'}"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "null"]
    log_level: str = "INFO"
    storage_backend: str = "local"  # local | supabase
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    supabase_bucket: str = "wardrobe-images"
    anthropic_api_key: str | None = None
    openweather_api_key: str | None = None
    agent_color_model: str = "claude-sonnet-4-20250514"
    agent_reasoning_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
