"""ResearchX configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/ai-service/app → ai-service → (apps → repo) OR deploy root when rootDir=apps/ai-service
APP_DIR = Path(__file__).resolve().parent
AI_SERVICE_ROOT = APP_DIR.parent
_monorepo_root = AI_SERVICE_ROOT.parent.parent
if (_monorepo_root / "apps" / "ai-service").is_dir() or (_monorepo_root / "evaluation").is_dir():
    REPO_ROOT = _monorepo_root
else:
    # Standalone PaaS deploy: treat the AI service folder as the root
    REPO_ROOT = AI_SERVICE_ROOT

# Data paths resolve against REPO_ROOT (monorepo or standalone).
ROOT_DIR = REPO_ROOT

_ENV_CANDIDATES = (
    AI_SERVICE_ROOT / ".env",
    REPO_ROOT / ".env",
)
_ENV_FILE = next((p for p in _ENV_CANDIDATES if p.exists()), AI_SERVICE_ROOT / ".env")


class Settings(BaseSettings):
    """Application settings for the ResearchX AI engine."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_provider: Literal["ollama", "groq", "gemini", "mock"] = "ollama"
    llm_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    groq_api_key: str = ""
    groq_api_key_2: str = ""
    groq_api_key_3: str = ""
    gemini_api_key: str = ""

    # Search
    search_provider: Literal["duckduckgo", "tavily", "serper"] = "duckduckgo"
    search_fallback: Literal["duckduckgo", "tavily", "serper"] = "duckduckgo"
    tavily_api_key: str = ""
    serper_api_key: str = ""

    # Pipeline limits
    max_sources: int = 20
    max_research_iterations: int = 2
    max_concurrent_agents: int = 3
    max_concurrent_research: int = 4
    max_concurrent_search: int = 5
    max_concurrent_llm_requests: int = 4
    max_research_time: int = 300
    max_content_length: int = 50_000
    max_search_queries: int = 20
    max_chunks: int = 500
    max_context_size: int = 12_000
    max_llm_calls: int = 40
    request_timeout: int = 30

    # Paths (relative to monorepo root)
    chroma_path: str = "./data/chroma"
    cache_path: str = "./data/cache"
    output_path: str = "./data/outputs"
    documents_path: str = "./data/documents"

    # Optional Redis (never required)
    redis_url: str = ""
    redis_ttl_seconds: int = 3600

    # Mode
    mock_mode: bool = False

    # API / FastAPI
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_debug: bool = False
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"
    app_version: str = "0.1.0"
    app_env: str = "development"
    # Shared secret for Express → FastAPI (empty disables auth in development)
    ai_service_token: str = ""
    max_concurrent_research_jobs: int = 4
    max_pdf_pages: int = 200
    max_document_pages: int = 200

    # Logging
    log_level: str = "INFO"

    @property
    def groq_api_keys(self) -> list[str]:
        """Primary + backup Groq keys (empty entries skipped, order preserved)."""
        keys: list[str] = []
        seen: set[str] = set()
        for raw in (self.groq_api_key, self.groq_api_key_2, self.groq_api_key_3):
            key = (raw or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            keys.append(key)
        return keys

    @property
    def effective_max_concurrent_jobs(self) -> int:
        """Prefer explicit max_concurrent_research when set via env."""
        return max(1, int(self.max_concurrent_research or self.max_concurrent_research_jobs or 1))

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS origins. Empty list means no origins (deny). Use explicit '*' only if configured."""
        raw = (self.cors_origins or "").strip()
        if not raw:
            return []
        return [o.strip() for o in raw.split(",") if o.strip()]

    def resolve_path(self, relative: str) -> Path:
        """Resolve a path relative to the monorepo root."""
        path = Path(relative)
        if path.is_absolute():
            return path
        return (ROOT_DIR / path).resolve()

    @property
    def cache_dir(self) -> Path:
        return self.resolve_path(self.cache_path)

    @property
    def output_dir(self) -> Path:
        return self.resolve_path(self.output_path)

    @property
    def documents_dir(self) -> Path:
        return self.resolve_path(self.documents_path)

    @property
    def chroma_dir(self) -> Path:
        return self.resolve_path(self.chroma_path)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    settings = Settings()
    for directory in (
        settings.cache_dir,
        settings.output_dir,
        settings.documents_dir,
        settings.chroma_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return settings
