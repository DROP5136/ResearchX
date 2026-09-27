"""Ollama local LLM provider (free / offline)."""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from providers.llm.base import LLMMessage, LLMProvider, LLMResponse
from utils.logging import get_logger

logger = get_logger("researchx.llm.ollama")


class OllamaProvider(LLMProvider):
    """Talks to a locally running Ollama server."""

    name = "ollama"

    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: int = 120):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if json_mode:
            payload["format"] = "json"

        url = f"{self.base_url}/api/chat"
        logger.debug("Ollama request model=%s", self.model)
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
            usage={
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            },
            raw=data,
        )
