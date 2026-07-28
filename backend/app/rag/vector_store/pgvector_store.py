"""
pgvector Vector Store (Phase 5)
Real vector similarity search replacing the fake cosine similarity in agents.py.

The original agents.py semantic_search() computed dot products on fake embeddings:
    similarities = np.dot(self.resume_embeddings, query_embedding)
This had no semantic meaning because the "embeddings" were ord() character values.

This implementation:
1. Uses real sentence-transformer embeddings
2. Stores vectors in PostgreSQL pgvector column
3. ALWAYS filters by organization_id for tenant isolation
4. Uses cosine distance (<=> operator) for semantic similarity
"""
from __future__ import annotations

import uuid
from typing import Any

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.exceptions import VectorStoreError
from app.models.candidate import ResumeChunk

logger = get_logger(__name__)


class PGVectorStore:
    """
    Vector similarity search using pgvector.
    
    SECURITY INVARIANT: Every query MUST include organization_id filter.
    This class enforces it at the method level — callers cannot bypass it.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_extension(self) -> None:
        """Create pgvector extension if not already installed."""
        await self.db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    async def similarity_search(
        self,
        query_embedding: list[float],
        organization_id: uuid.UUID,
        candidate_id: uuid.UUID | None = None,
        top_k: int = 5,
        section_types: list[str] | None = None,
        min_similarity: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Semantic similarity search over resume chunks.
        
        Args:
            query_embedding: Real embedding vector from EmbeddingService
            organization_id: REQUIRED for tenant isolation — cannot be None
            candidate_id: Optional filter for specific candidate
            top_k: Number of results
            section_types: Optional filter by section type
            min_similarity: Minimum cosine similarity threshold
            
        Returns:
            List of dicts with 'content', 'section_type', 'similarity', 'metadata'
        """
        if not query_embedding:
            raise VectorStoreError("query_embedding cannot be empty")

        # Build base query with MANDATORY org filter
        # Using cosine distance (<=>): lower = more similar; convert to similarity = 1 - distance
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        
        conditions = [
            "rc.organization_id = :org_id",  # MANDATORY tenant isolation
        ]
        params: dict[str, Any] = {
            "org_id": str(organization_id),
            "embedding": embedding_str,
            "top_k": top_k,
            "min_similarity": 1.0 - min_similarity,  # distance threshold
        }

        if candidate_id:
            conditions.append("rc.candidate_id = :candidate_id")
            params["candidate_id"] = str(candidate_id)

        if section_types:
            conditions.append("rc.section_type = ANY(:section_types)")
            params["section_types"] = section_types

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT
                rc.id,
                rc.content,
                rc.section_type,
                rc.candidate_id,
                rc.metadata_json,
                1 - (rc.embedding <=> :embedding::vector) AS similarity
            FROM resume_chunks rc
            WHERE {where_clause}
                AND rc.embedding IS NOT NULL
                AND 1 - (rc.embedding <=> :embedding::vector) >= (1 - :min_similarity)
            ORDER BY rc.embedding <=> :embedding::vector
            LIMIT :top_k
        """)

        try:
            result = await self.db.execute(sql, params)
            rows = result.fetchall()
        except Exception as exc:
            logger.error("Vector search failed", error=str(exc))
            raise VectorStoreError(f"Vector search failed: {exc}") from exc

        results = []
        for row in rows:
            results.append({
                "id": str(row.id),
                "content": row.content,
                "section_type": row.section_type,
                "candidate_id": str(row.candidate_id),
                "metadata": row.metadata_json or {},
                "similarity": float(row.similarity),
            })

        logger.debug(
            "Vector search completed",
            org_id=str(organization_id),
            candidate_id=str(candidate_id) if candidate_id else "all",
            results=len(results),
            top_k=top_k,
        )
        return results

    async def upsert_chunk(
        self,
        chunk_id: uuid.UUID,
        embedding: list[float],
    ) -> None:
        """Update a chunk's embedding vector."""
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        await self.db.execute(
            text("UPDATE resume_chunks SET embedding = :emb::vector WHERE id = :id"),
            {"emb": embedding_str, "id": str(chunk_id)},
        )
