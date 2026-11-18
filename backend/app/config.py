"""Application configuration for PitWall AI."""

from dataclasses import dataclass
import os
from urllib.parse import urlparse


def _environment_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _environment_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


@dataclass(frozen=True)
class Settings:
    """Runtime settings with development-safe defaults."""

    app_title: str = "PitWall AI Backend"
    app_version: str = "0.1.0"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./pitwall_ai.db")
    ai_provider: str = os.getenv("AI_PROVIDER", "deterministic")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    f1_data_provider: str = os.getenv("F1_DATA_PROVIDER", "jolpica")


@dataclass(frozen=True)
class JolpicaSettings:
    """Validated runtime configuration for the key-free Jolpica provider."""

    base_url: str = "https://api.jolpi.ca"
    user_agent: str = "PitWallAI/0.1.0"
    connect_timeout_seconds: float = 3.0
    read_timeout_seconds: float = 10.0
    retry_limit: int = 2
    max_retry_delay_seconds: float = 5.0
    page_size: int = 100
    max_pages: int = 100

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("JOLPICA_BASE_URL must be an absolute HTTP(S) URL")
        if not self.user_agent.strip():
            raise ValueError("JOLPICA_USER_AGENT must not be empty")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("Jolpica timeouts must be positive")
        if not 0 <= self.retry_limit <= 5:
            raise ValueError("JOLPICA_RETRY_LIMIT must be between 0 and 5")
        if self.max_retry_delay_seconds <= 0:
            raise ValueError("JOLPICA_MAX_RETRY_DELAY_SECONDS must be positive")
        if not 1 <= self.page_size <= 100:
            raise ValueError("JOLPICA_PAGE_SIZE must be between 1 and 100")
        if self.max_pages <= 0:
            raise ValueError("JOLPICA_MAX_PAGES must be positive")

    @classmethod
    def from_environment(cls) -> "JolpicaSettings":
        return cls(
            base_url=os.getenv("JOLPICA_BASE_URL", cls.base_url),
            user_agent=os.getenv("JOLPICA_USER_AGENT", cls.user_agent),
            connect_timeout_seconds=_environment_float("JOLPICA_CONNECT_TIMEOUT_SECONDS", 3.0),
            read_timeout_seconds=_environment_float("JOLPICA_READ_TIMEOUT_SECONDS", 10.0),
            retry_limit=_environment_int("JOLPICA_RETRY_LIMIT", 2),
            max_retry_delay_seconds=_environment_float("JOLPICA_MAX_RETRY_DELAY_SECONDS", 5.0),
            page_size=_environment_int("JOLPICA_PAGE_SIZE", 100),
            max_pages=_environment_int("JOLPICA_MAX_PAGES", 100),
        )


@dataclass(frozen=True)
class OpenF1Settings:
    """Validated configuration for the approved secondary weather provider."""

    base_url: str = "https://api.openf1.org"
    connect_timeout_seconds: float = 3.0
    read_timeout_seconds: float = 10.0
    retry_limit: int = 2
    max_retry_delay_seconds: float = 5.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("OPENF1_BASE_URL must be an absolute HTTP(S) URL")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("OpenF1 timeouts must be positive")
        if not 0 <= self.retry_limit <= 5:
            raise ValueError("OPENF1_RETRY_LIMIT must be between 0 and 5")
        if self.max_retry_delay_seconds <= 0:
            raise ValueError("OPENF1_MAX_RETRY_DELAY_SECONDS must be positive")

    @classmethod
    def from_environment(cls) -> "OpenF1Settings":
        return cls(
            base_url=os.getenv("OPENF1_BASE_URL", cls.base_url),
            connect_timeout_seconds=_environment_float("OPENF1_CONNECT_TIMEOUT_SECONDS", 3.0),
            read_timeout_seconds=_environment_float("OPENF1_READ_TIMEOUT_SECONDS", 10.0),
            retry_limit=_environment_int("OPENF1_RETRY_LIMIT", 2),
            max_retry_delay_seconds=_environment_float("OPENF1_MAX_RETRY_DELAY_SECONDS", 5.0),
        )


settings = Settings()
