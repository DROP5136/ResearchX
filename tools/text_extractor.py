"""Clean text extraction from HTML using trafilatura / BeautifulSoup."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from utils.helpers import truncate
from utils.logging import get_logger

logger = get_logger("researchx.tools.extract")


class TextExtractor:
    """Extract main article text from HTML."""

    def extract(self, html: str, max_length: int = 50_000) -> str:
        if not html:
            return ""
        text = self._trafilatura(html) or self._beautifulsoup(html)
        text = self._normalize(text)
        return truncate(text, max_length)

    def relevant_passages(self, text: str, query: str, max_passages: int = 5, window: int = 400) -> list[str]:
        """Simple keyword-overlap passage ranking."""
        if not text:
            return []
        paragraphs = [p.strip() for p in re.split(r"\n{2,}|(?<=\.)\s+(?=[A-Z])", text) if len(p.strip()) > 40]
        if not paragraphs:
            return [truncate(text, window)]
        tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9%$.+-]+", query) if len(t) > 2}
        scored: list[tuple[int, str]] = []
        for p in paragraphs:
            pl = p.lower()
            score = sum(1 for t in tokens if t in pl)
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        passages = [truncate(p, window) for s, p in scored[:max_passages] if s > 0]
        if not passages:
            passages = [truncate(p, window) for _, p in scored[:max_passages]]
        return passages

    @staticmethod
    def _trafilatura(html: str) -> str:
        try:
            import trafilatura

            extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
            return extracted or ""
        except Exception as exc:  # noqa: BLE001
            logger.debug("trafilatura failed: %s", exc)
            return ""

    @staticmethod
    def _beautifulsoup(html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup.get_text("\n", strip=True)

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
