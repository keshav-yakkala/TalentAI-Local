"""
Embedding Service (Phase 5)
Real semantic embeddings replacing the fake word-ordinal hash from agents.py.
Supports sentence-transformers (local), Ollama, and Gemini.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np

from app.core.config import settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseEmbeddingProvider(ABC):
    """Abstract embedding provider. All providers return numpy float32 arrays."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimensionality."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string. Returns list of floats."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple strings. More efficient than calling embed() in a loop."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


class SentenceTransformerProvider(BaseEmbeddingProvider):
    """
    Local sentence-transformers embedding.
    Model: all-MiniLM-L6-v2 (384 dims, fast, good quality)
    No API key needed. Runs locally.
    
    This REPLACES the fake embed_text() function in agents.py that did:
        vector = [ord(c) % 100 for c in text...]
    which produced meaningless embeddings with no semantic content.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None  # Lazy load

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading embedding model", model=self._model_name)
                self._model = SentenceTransformer(self._model_name)
                logger.info("Embedding model loaded", model=self._model_name)
            except ImportError as exc:
                raise EmbeddingError(
                    "sentence-transformers not installed. Run: pip install sentence-transformers"
                ) from exc
        return self._model

    async def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            return [0.0] * self.dimension
        try:
            import asyncio
            model = self._get_model()
            # Run CPU-bound embedding in thread pool to not block async loop
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: model.encode(text, normalize_embeddings=True).tolist()
            )
            return embedding
        except Exception as exc:
            raise EmbeddingError(f"Embedding failed: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            import asyncio
            model = self._get_model()
            # Filter empty texts, track indices
            indexed = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
            if not indexed:
                return [[0.0] * self.dimension] * len(texts)

            indices, valid_texts = zip(*indexed)
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: model.encode(list(valid_texts), normalize_embeddings=True, batch_size=32).tolist()
            )

            # Map back to original positions
            result = [[0.0] * self.dimension] * len(texts)
            for idx, emb in zip(indices, embeddings):
                result[idx] = emb
            return result
        except Exception as exc:
            raise EmbeddingError(f"Batch embedding failed: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            emb = await self.embed("health check")
            return len(emb) == self.dimension
        except Exception:
            return False


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Embeddings via Ollama /api/embeddings endpoint."""

    def __init__(self, model: str = "nomic-embed-text") -> None:
        self._model = model

    @property
    def dimension(self) -> int:
        return 768  # nomic-embed-text dimension

    async def embed(self, text: str) -> list[float]:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                resp.raise_for_status()
                return resp.json()["embedding"]
        except Exception as exc:
            raise EmbeddingError(f"Ollama embedding failed: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Ollama doesn't support batch — call serially
        results = []
        for text in texts:
            results.append(await self.embed(text))
        return results

    async def health_check(self) -> bool:
        try:
            emb = await self.embed("test")
            return len(emb) > 0
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_embedding_provider() -> BaseEmbeddingProvider:
    """Return the configured embedding provider singleton."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "sentence_transformers":
        return SentenceTransformerProvider()
    elif provider == "ollama":
        return OllamaEmbeddingProvider()
    else:
        raise EmbeddingError(f"Unknown embedding provider: {provider}")
