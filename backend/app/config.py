"""Application configuration for PitWall AI."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Runtime settings with development-safe defaults."""

    app_title: str = "PitWall AI Backend"
    app_version: str = "0.1.0"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./pitwall_ai.db")
    ai_provider: str = os.getenv("AI_PROVIDER", "deterministic")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")


settings = Settings()
