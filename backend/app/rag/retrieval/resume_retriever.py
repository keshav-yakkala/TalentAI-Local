"""
Resume Retriever (Phase 5) — RAG Q&A
Handles the "ask a question about a resume" feature from the original app.

The original agents.py ask_question() sent the ENTIRE resume text to the LLM.
This implementation:
1. Embeds the question with real semantic embeddings
2. Retrieves only the relevant chunks via pgvector
3. Uses those chunks as context (true RAG)
4. Enforces tenant isolation on every retrieval
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.local_provider import get_embedding_provider
from app.ai.llms.factory import get_llm_provider
from app.core.config import settings
from app.core.logging import get_logger
from app.rag.vector_store.pgvector_store import PGVectorStore

logger = get_logger(__name__)


class ResumeRetriever:
    """
    RAG-powered resume Q&A.
    Replaces the original full-context LLM call with proper retrieval.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.vector_store = PGVectorStore(db)
        self.embedding_provider = get_embedding_provider()
        self.llm = get_llm_provider()

    async def answer_question(
        self,
        question: str,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        """
        Answer a question about a candidate's resume using RAG.
        
        Flow: Embed question → Vector search (org-scoped) → LLM with context
        
        Returns dict with 'answer', 'evidence', 'confidence', 'sources'
        """
        top_k = top_k or settings.RAG_TOP_K

        # 1. Embed the question
        question_embedding = await self.embedding_provider.embed(question)

        # 2. Retrieve relevant chunks — ALWAYS org-scoped
        chunks = await self.vector_store.similarity_search(
            query_embedding=question_embedding,
            organization_id=organization_id,
            candidate_id=candidate_id,
            top_k=top_k,
            min_similarity=0.25,
        )

        if not chunks:
            return {
                "answer": "I couldn't find relevant information in the resume to answer this question.",
                "evidence": [],
                "confidence": 0.0,
                "sources": [],
            }

        # 3. Build context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[{i}] [{chunk['section_type'].upper()}] {chunk['content']}"
            )
        context = "\n\n".join(context_parts)

        # 4. LLM generation with retrieved context only
        prompt = f"""You are a helpful AI assistant that answers questions about a candidate's resume.
Use ONLY the information provided in the resume excerpts below.
If the information is not present, say "This information is not in the resume."
Do NOT infer, guess, or add information not explicitly stated.

Resume Excerpts:
{context}

Question: {question}

Answer based strictly on the resume content above:"""

        answer = await self.llm.generate(prompt)

        return {
            "answer": answer,
            "evidence": [
                {
                    "content": c["content"][:200],
                    "section_type": c["section_type"],
                    "similarity": round(c["similarity"], 3),
                }
                for c in chunks
            ],
            "confidence": chunks[0]["similarity"] if chunks else 0.0,
            "sources": [c["section_type"] for c in chunks],
        }
