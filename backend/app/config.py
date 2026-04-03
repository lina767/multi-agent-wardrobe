from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WARDROBE_",
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database_url: str = f"sqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'wardrobe.db'}"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",
    ]
    log_level: str = "INFO"
    storage_backend: str = "local"  # local | supabase
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_key: str | None = None
    supabase_jwt_secret: str | None = None
    supabase_bucket: str = "wardrobe-images"
    auth_redirect_url: str = "http://127.0.0.1:8000/auth/callback"
    anthropic_api_key: str | None = None
    weather_api_key: str | None = None
    agent_color_model: str = "claude-sonnet-4-20250514"
    agent_reasoning_model: str = "claude-haiku-4-5-20251001"
    color_agent_backend: str = "anthropic_vision"  # anthropic_vision | fine_tuned | heuristic
    color_fine_tuned_endpoint: str | None = None
    color_profile_min_confidence: float = 0.65
    color_agent_shadow_mode: bool = False
    vector_store_backend: str = "none"  # none | pinecone | azure_ai_search
    vector_search_top_k: int = 12
    vector_embedding_provider: str = "endpoint"  # endpoint | huggingface
    vector_embedding_endpoint: str | None = None
    vector_embedding_api_key: str | None = None
    vector_embedding_model: str | None = None
    huggingface_embedding_api_key: str | None = None
    huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    huggingface_embedding_endpoint: str | None = None
    pinecone_api_key: str | None = None
    pinecone_index_host: str | None = None
    pinecone_namespace: str | None = None
    azure_search_endpoint: str | None = None
    azure_search_api_key: str | None = None
    azure_search_index_name: str | None = None
    azure_search_vector_field: str = "content_vector"
    azure_search_item_id_field: str = "item_id"
    vision_enabled: bool = False
    hf_api_token: str | None = None
    hf_tagging_model: str = "openai/clip-vit-base-patch32"
    hf_rmbg_model: str = "briaai/RMBG-1.4"
    hf_timeout_seconds: float = 20.0
    hf_max_retries: int = 2
    calendar_events_json: str | None = None
    google_calendar_access_token: str | None = None
    google_calendar_ids: list[str] = ["primary"]
    google_calendar_client_id: str | None = None
    google_calendar_client_secret: str | None = None
    google_calendar_refresh_token: str | None = None


settings = Settings()
