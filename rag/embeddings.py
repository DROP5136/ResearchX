"""Embedding helpers using FastEmbed (local, free)."""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from utils.logging import get_logger

logger = get_logger("researchx.rag.embeddings")

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


class EmbeddingModel:
    """Thin wrapper around FastEmbed TextEmbedding."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None

    def _ensure(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise RuntimeError("fastembed is not installed") from exc
            logger.info("Loading embedding model %s", self.model_name)
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._ensure()
        return [list(vec) for vec in model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


@lru_cache
def get_embedder(model_name: str = DEFAULT_MODEL) -> EmbeddingModel:
    return EmbeddingModel(model_name=model_name)
