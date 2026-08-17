"""
Viva — Application Configuration
All settings are loaded from environment variables via Pydantic Settings.
Never hardcode secrets — add them to .env (gitignored).
"""
from functools import lru_cache
from typing import List

import warnings
from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "Viva"
    environment: str = "development"
    port: int = 8000

    # --- Database ---
    database_url: str = Field(..., description="asyncpg-compatible postgres URL")

    # --- Groq (LLM via OpenAI SDK) ---
    groq_api_key: str = Field(..., description="Groq API key from console.groq.com")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model_generation: str = "llama-3.3-70b-versatile"
    groq_model_scoring: str = "llama-3.1-8b-instant"

    # --- Embeddings ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # --- Ingestion ---
    books_dir: str = "data/books"
    chunk_size_tokens: int = 600
    chunk_overlap_tokens: int = 80
    similarity_dedup_threshold: float = 0.93

    # --- Adaptive engine ---
    difficulty_adjust_step: float = 0.15
    initial_question_count: int = 5
    max_adaptive_followups: int = 3

    # --- CORS ---
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        # Stored as a string; split into list in get_allowed_origins()
        return v

    @field_validator("allowed_origins", mode="after")
    @classmethod
    def check_wildcard_in_production(cls, v: str, info: ValidationInfo) -> str:
        origins = [o.strip() for o in v.split(",") if o.strip()]
        if "*" in origins and info.data.get("environment") == "production":
            warnings.warn("CORS wildcard '*' is allowed in production environment, which is a security risk!")
        return v

    def get_allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # --- Resume upload ---
    max_resume_size_mb: int = 5
    rate_limit_resume: str = "5/minute"
    rate_limit_session: str = "10/minute"

    @property
    def max_resume_size_bytes(self) -> int:
        return self.max_resume_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings singleton. Import this everywhere, not Settings()."""
    return Settings()
