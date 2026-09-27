"""Groq LLM provider with multi-key failover on rate limits."""

from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.providers.llm.base import LLMMessage, LLMProvider, LLMResponse
from app.utils.logging import get_logger

logger = get_logger("researchx.llm.groq")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


def _is_network_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def _is_rate_limited(status_code: int, body: str) -> bool:
    if status_code == 429:
        return True
    lowered = (body or "").lower()
    return "rate_limit" in lowered or "rate limit" in lowered or "tokens per day" in lowered


def _dedupe_keys(*groups: str | list[str] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        if group is None:
            continue
        values = group if isinstance(group, list) else [group]
        for raw in values:
            key = (raw or "").strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


class GroqProvider(LLMProvider):
    """Groq OpenAI-compatible chat completions API.

    Supports multiple API keys. On rate-limit (HTTP 429), the provider
    automatically rotates to the next configured key.
    """

    name = "groq"

    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_GROQ_MODEL,
        timeout: int = 60,
        api_keys: list[str] | None = None,
    ):
        keys = _dedupe_keys(api_key, api_keys)
        if not keys:
            raise ValueError(
                "At least one Groq API key is required "
                "(GROQ_API_KEY / GROQ_API_KEY_2 / GROQ_API_KEY_3)"
            )
        self.api_keys = keys
        self._key_index = 0
        self.api_key = keys[0]  # back-compat attribute
        self.model = model or DEFAULT_GROQ_MODEL
        self.timeout = timeout

    @property
    def active_key_index(self) -> int:
        return self._key_index

    def _current_key(self) -> str:
        return self.api_keys[self._key_index]

    def _rotate_key(self) -> bool:
        """Advance to the next unused key. Returns False if none remain."""
        if self._key_index + 1 >= len(self.api_keys):
            return False
        self._key_index += 1
        self.api_key = self._current_key()
        logger.warning(
            "Groq rate limited — rotating to backup key %d/%d",
            self._key_index + 1,
            len(self.api_keys),
        )
        return True

    @retry(
        retry=retry_if_exception(_is_network_retryable),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=20),
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
        payload: dict = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        # Try current key, then any remaining backups on rate limit
        attempts_left = len(self.api_keys) - self._key_index
        for _ in range(max(1, attempts_left)):
            headers = {
                "Authorization": f"Bearer {self._current_key()}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(GROQ_API_URL, json=payload, headers=headers)
                if resp.status_code < 400:
                    data = resp.json()
                    message = (data.get("choices") or [{}])[0].get("message") or {}
                    # gpt-oss models may fill `reasoning` first; content can be empty
                    # when max_tokens is too low for both reasoning + answer.
                    content = (message.get("content") or "").strip()
                    if not content:
                        content = (message.get("reasoning") or "").strip()
                    return LLMResponse(
                        content=content,
                        model=self.model,
                        provider=self.name,
                        usage=data.get("usage", {}),
                        raw=data,
                    )

                detail = resp.text[:500]
                if _is_rate_limited(resp.status_code, detail):
                    last_error = RuntimeError(f"Groq HTTP {resp.status_code}: {detail}")
                    if self._rotate_key():
                        continue
                    break
                raise RuntimeError(f"Groq HTTP {resp.status_code}: {detail}")

        raise last_error or RuntimeError("Groq request failed after exhausting API keys")
