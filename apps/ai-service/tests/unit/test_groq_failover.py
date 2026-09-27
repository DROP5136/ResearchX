"""Tests for Groq multi-key rate-limit failover."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.providers.llm.base import LLMMessage
from app.providers.llm.groq import GroqProvider, _dedupe_keys


def test_dedupe_keys_preserves_order():
    assert _dedupe_keys("a", ["b", "a", "c", ""], "b") == ["a", "b", "c"]


def test_groq_requires_at_least_one_key():
    with pytest.raises(ValueError, match="At least one Groq API key"):
        GroqProvider(api_key="", api_keys=[])


def test_groq_rotates_on_rate_limit():
    provider = GroqProvider(api_keys=["key-primary", "key-backup"])
    messages = [LLMMessage(role="user", content="hi")]

    rate_limited = MagicMock()
    rate_limited.status_code = 429
    rate_limited.text = '{"error":{"message":"Rate limit exceeded"}}'

    ok = MagicMock()
    ok.status_code = 200
    ok.json.return_value = {
        "choices": [{"message": {"content": "ok-from-backup"}}],
        "usage": {"total_tokens": 3},
    }

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.side_effect = [rate_limited, ok]

    with patch("app.providers.llm.groq.httpx.Client", return_value=mock_client):
        resp = provider.generate(messages)

    assert resp.content == "ok-from-backup"
    assert provider.active_key_index == 1
    assert mock_client.post.call_count == 2
    first_auth = mock_client.post.call_args_list[0].kwargs["headers"]["Authorization"]
    second_auth = mock_client.post.call_args_list[1].kwargs["headers"]["Authorization"]
    assert first_auth == "Bearer key-primary"
    assert second_auth == "Bearer key-backup"


def test_groq_exhausts_all_keys():
    provider = GroqProvider(api_keys=["k1", "k2"])
    messages = [LLMMessage(role="user", content="hi")]

    limited = MagicMock()
    limited.status_code = 429
    limited.text = "rate_limit"

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False
    mock_client.post.return_value = limited

    with patch("app.providers.llm.groq.httpx.Client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="429"):
            provider.generate(messages)

    assert mock_client.post.call_count == 2
