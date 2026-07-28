"""
TalentAI — Domain Exceptions
All application-specific exceptions live here.
API handlers map these to safe HTTP responses.
Stack traces and internal details are NEVER exposed to clients.
"""
from typing import Any


class TalentAIBaseError(Exception):
    """Base for all TalentAI exceptions."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ── Auth ──────────────────────────────────────────────────────────────────────


class AuthenticationError(TalentAIBaseError):
    """Invalid credentials or expired token."""


class AuthorizationError(TalentAIBaseError):
    """Caller does not have permission to perform this action."""


class TokenExpiredError(AuthenticationError):
    """JWT access token has expired."""


# ── Resume ────────────────────────────────────────────────────────────────────


class ResumeParsingError(TalentAIBaseError):
    """Failed to extract text from a resume file."""


class UnsupportedFileError(TalentAIBaseError):
    """File format is not supported."""


class FileTooLargeError(TalentAIBaseError):
    """Uploaded file exceeds the maximum allowed size."""


class ResumeNotFoundError(TalentAIBaseError):
    """Requested resume does not exist or is not accessible."""


# ── AI / LLM ─────────────────────────────────────────────────────────────────


class LLMProviderError(TalentAIBaseError):
    """LLM provider returned an error or is unavailable."""


class LLMOutputValidationError(TalentAIBaseError):
    """LLM output failed Pydantic schema validation after max retries."""


class EmbeddingError(TalentAIBaseError):
    """Failed to generate embeddings."""


class TranscriptionError(TalentAIBaseError):
    """Whisper transcription failed."""


# ── RAG / Vector Store ────────────────────────────────────────────────────────


class VectorStoreError(TalentAIBaseError):
    """pgvector operation failed."""


class RetrievalError(TalentAIBaseError):
    """Failed to retrieve relevant chunks."""


# ── Workflow / LangGraph ──────────────────────────────────────────────────────


class WorkflowError(TalentAIBaseError):
    """LangGraph workflow encountered an unrecoverable error."""


class WorkflowNotFoundError(TalentAIBaseError):
    """Requested workflow run does not exist."""


class MaxRetriesExceededError(WorkflowError):
    """Workflow node exhausted its retry budget."""


# ── Business Logic ────────────────────────────────────────────────────────────


class JobNotFoundError(TalentAIBaseError):
    """Job posting does not exist or belongs to another organization."""


class CandidateNotFoundError(TalentAIBaseError):
    """Candidate profile not found."""


class ApplicationNotFoundError(TalentAIBaseError):
    """Application record not found."""


class InterviewNotFoundError(TalentAIBaseError):
    """Interview session not found."""


class DuplicateApplicationError(TalentAIBaseError):
    """Candidate has already applied to this job."""


class InvalidScoringWeightsError(TalentAIBaseError):
    """Screening weight configuration does not sum to 1.0."""


# ── Multi-tenancy ─────────────────────────────────────────────────────────────


class CrossTenantAccessError(AuthorizationError):
    """
    Attempt to access data belonging to a different organization.
    This is a critical security violation and must be logged as CRITICAL.
    """
