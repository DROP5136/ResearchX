"""Google Gemini LLM provider."""

from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse
from app.utils.logging import get_logger

logger = get_logger("researchx.llm.gemini")

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.status_code in {429, 500, 502, 503, 504}
    if isinstance(exc, RuntimeError) and "429" in str(exc):
        return True
    return False


class GeminiProvider(LLMProvider):
    """Google Generative Language API (Gemini)."""

    name = "gemini"

    def __init__(self, api_key: str, model: str = DEFAULT_GEMINI_MODEL, timeout: int = 60):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for GeminiProvider")
        self.api_key = api_key
        self.model = model or DEFAULT_GEMINI_MODEL
        self.timeout = timeout

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        reraise=True,
    )
    def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        contents = []
        for m in messages:
            if m.role == "system":
                continue
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        if not contents:
            contents = [{"role": "user", "parts": [{"text": "Hello"}]}]

        generation_config: dict = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload: dict = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code >= 400:
                detail = resp.text[:400]
                # Raise HTTPStatusError so tenacity can retry 429s
                raise httpx.HTTPStatusError(
                    f"Gemini HTTP {resp.status_code}: {detail}",
                    request=resp.request,
                    response=resp,
                )
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {data}")
        parts = candidates[0].get("content", {}).get("parts", [])
        content = "".join(p.get("text", "") for p in parts)
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
            usage=data.get("usageMetadata", {}),
            raw=data,
        )
