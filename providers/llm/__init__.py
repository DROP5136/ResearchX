"""LLM provider factory."""

from __future__ import annotations

from config import Settings, get_settings
from providers.llm.base import LLMProvider
from providers.llm.gemini import GeminiProvider
from providers.llm.groq import GroqProvider
from providers.llm.mock import MockLLMProvider
from providers.llm.ollama import OllamaProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Instantiate the configured LLM provider."""
    settings = settings or get_settings()
    if settings.mock_mode or settings.llm_provider == "mock":
        return MockLLMProvider(model=settings.llm_model or "mock-model")

    provider = settings.llm_provider.lower()
    if provider == "ollama":
        return OllamaProvider(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            timeout=settings.request_timeout * 4,
        )
    if provider == "groq":
        return GroqProvider(
            api_key=settings.groq_api_key,
            api_keys=settings.groq_api_keys,
            model=settings.llm_model,
            timeout=settings.request_timeout * 2,
        )
    if provider == "gemini":
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.llm_model)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


__all__ = [
    "GeminiProvider",
    "GroqProvider",
    "LLMProvider",
    "MockLLMProvider",
    "OllamaProvider",
    "get_llm_provider",
]
