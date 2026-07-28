"""
Resume Ingestion LangGraph — State definition.
Represents the complete state of a resume ingestion workflow run.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.ai.structured_outputs.resume import ResumeProfile


class ResumeIngestionState(BaseModel):
    """
    Immutable-style state passed between LangGraph nodes.
    Each node returns a partial update; LangGraph merges them.

    IMPORTANT: retry_count + max_retries prevents infinite loops.
    """

    # Identifiers
    workflow_id: str
    organization_id: str
    candidate_id: str
    resume_id: str

    # File
    file_path: str
    file_type: str  # pdf, docx, txt
    file_content_bytes: bytes | None = None

    # Extraction pipeline
    raw_text: str | None = None
    cleaned_text: str | None = None
    sections: dict[str, str] = Field(default_factory=dict)  # section_type → content
    structured_resume: ResumeProfile | None = None

    # Chunking and embeddings
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    embedding_status: str = "pending"  # pending, generating, completed, failed

    # Quality
    extraction_confidence: float = 0.0
    validation_errors: list[str] = Field(default_factory=list)

    # Control flow
    retry_count: int = 0
    max_retries: int = 3
    current_status: str = "pending"  # pending, parsing, extracting, embedding, completed, failed, human_review_required
    requires_human_review: bool = False
    human_review_reason: str | None = None

    # Error tracking
    errors: list[str] = Field(default_factory=list)

    def add_error(self, error: str) -> "ResumeIngestionState":
        """Return a new state with the error appended."""
        return self.model_copy(update={"errors": [*self.errors, error]})

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries
