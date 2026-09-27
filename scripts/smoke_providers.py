"""Quick provider smoke test (does not print secrets)."""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import get_settings
from providers.llm.gemini import GeminiProvider
from providers.llm.groq import GroqProvider
from providers.search.serper import SerperProvider
from providers.search.tavily import TavilyProvider


def main() -> None:
    get_settings.cache_clear()
    s = get_settings()

    print("=== Groq model list ===")
    try:
        resp = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {s.groq_api_key}"},
            timeout=30,
        )
        print("status:", resp.status_code)
        if resp.status_code == 200:
            ids = sorted(m["id"] for m in resp.json().get("data", []))
            print("models:", ", ".join(ids[:15]) or "(none)")
            if ids:
                model = ids[0]
                out = GroqProvider(s.groq_api_key, model=model).complete(
                    'Return JSON {"ok": true}',
                    system="Reply with JSON only.",
                    json_mode=True,
                )
                print("chat ok with", model, "->", out[:100].replace("\n", " "))
        else:
            print("body:", resp.text[:300])
    except Exception as exc:  # noqa: BLE001
        print("FAIL:", type(exc).__name__, str(exc)[:300])

    for model in ("gemini-2.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"):
        print(f"=== Gemini {model} ===")
        try:
            out = GeminiProvider(s.gemini_api_key, model=model).complete(
                'Return JSON {"ok": true}',
                system="Reply with JSON only.",
                json_mode=True,
            )
            print("ok:", out[:120].replace("\n", " "))
            break
        except Exception as exc:  # noqa: BLE001
            print("FAIL:", type(exc).__name__, str(exc)[:220])

    print("=== Tavily ===")
    try:
        hits = TavilyProvider(api_key=s.tavily_api_key).search(
            "India EV market size 2024", max_results=3
        )
        print("hits:", len(hits))
        for h in hits:
            print("-", h.title[:80])
    except Exception as exc:  # noqa: BLE001
        print("FAIL:", type(exc).__name__, str(exc)[:300])

    print("=== Serper ===")
    try:
        hits = SerperProvider(api_key=s.serper_api_key).search(
            "India EV market size 2024", max_results=3
        )
        print("hits:", len(hits))
        for h in hits:
            print("-", h.title[:80])
    except Exception as exc:  # noqa: BLE001
        print("FAIL:", type(exc).__name__, str(exc)[:300])


if __name__ == "__main__":
    main()
