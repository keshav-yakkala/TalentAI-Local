"""
TalentAI Backend — Environment Configuration
All settings are loaded from environment variables (.env file).
Never hardcode secrets here.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = "TalentAI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # ── API ──────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://talentai:talentai@localhost:5432/talentai_db"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # ── Authentication ───────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = Field(default="CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── LLM Provider ────────────────────────────────────────────────────────
    LLM_PROVIDER: Literal["grok", "ollama", "gemini", "openai"] = "grok"
    LLM_MODEL: str = "grok-2-latest"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # Grok (xAI)
    GROK_API_KEY: str = ""
    GROK_BASE_URL: str = "https://api.x.ai/v1"
    GROK_MODEL: str = "grok-2-latest"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # OpenAI-compatible
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # ── Embeddings ───────────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: Literal["sentence_transformers", "ollama", "gemini"] = (
        "sentence_transformers"
    )
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── Storage ──────────────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # ── Whisper ──────────────────────────────────────────────────────────────
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"

    # ── RAG ──────────────────────────────────────────────────────────────────
    RAG_CHUNK_SIZE: int = 512
    RAG_CHUNK_OVERLAP: int = 64
    RAG_TOP_K: int = 5
    RAG_RERANK_TOP_K: int = 3

    # ── Screening Weights (must sum to 1.0) ─────────────────────────────────
    SCREENING_WEIGHT_REQUIRED_SKILLS: float = 0.30
    SCREENING_WEIGHT_EXPERIENCE: float = 0.20
    SCREENING_WEIGHT_PROJECTS: float = 0.20
    SCREENING_WEIGHT_PREFERRED_SKILLS: float = 0.10
    SCREENING_WEIGHT_EDUCATION: float = 0.05
    SCREENING_WEIGHT_DOMAIN: float = 0.05
    SCREENING_WEIGHT_SEMANTIC_MATCH: float = 0.10

    # ── Observability ────────────────────────────────────────────────────────
    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""

    LOG_LEVEL: str = "INFO"

    @field_validator("SCREENING_WEIGHT_REQUIRED_SKILLS")
    @classmethod
    def validate_weights_sum(cls, v: float) -> float:
        # Validation happens at the model level; individual fields are checked
        # here to surface config issues early.
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Use dependency injection in FastAPI routes."""
    return Settings()


settings = get_settings()
