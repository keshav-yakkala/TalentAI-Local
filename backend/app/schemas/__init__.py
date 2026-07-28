"""
Pydantic v2 schemas for Auth, User, Organization, Job, Resume, Application,
Screening, Interview, and common response types.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.models.organization import OrgMemberRole
from app.models.job import JobStatus, EmploymentType, RequirementType, RequirementImportance
from app.models.candidate import ParsingStatus, ResumeSectionType
from app.models.application import (
    ApplicationStatus,
    ScreeningRecommendation,
    InterviewStatus,
    InterviewDifficulty,
    QuestionType,
)


# ── Common ────────────────────────────────────────────────────────────────────


class APIResponse(BaseModel):
    """Generic success response envelope."""

    success: bool = True
    message: str = "OK"
    data: Any = None


class ErrorResponse(BaseModel):
    """Safe error response — never expose stack traces or internal details."""

    success: bool = False
    error: str
    code: str | None = None


class PaginatedResponse(BaseModel):
    """Paginated list response."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int


# ── Auth ──────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=256)
    role: UserRole = UserRole.candidate


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


# ── Organization ──────────────────────────────────────────────────────────────


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


# ── Job ───────────────────────────────────────────────────────────────────────


class JobRequirementIn(BaseModel):
    requirement_type: RequirementType
    name: str = Field(max_length=256)
    importance: RequirementImportance = RequirementImportance.must_have
    weight: float | None = None
    minimum_level: str | None = None


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType | None = None
    requirements: list[JobRequirementIn] = []


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    department: str | None = None
    location: str | None = None
    employment_type: EmploymentType | None = None
    status: JobStatus | None = None


class JobRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_type: RequirementType
    name: str
    importance: RequirementImportance
    weight: float | None
    minimum_level: str | None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str | None
    department: str | None
    location: str | None
    employment_type: EmploymentType | None
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    requirements: list[JobRequirementOut] = []


class JDAnalyzeRequest(BaseModel):
    """Submit raw JD text for AI-powered requirement extraction."""

    jd_text: str = Field(min_length=50, max_length=50_000)


# ── Resume ────────────────────────────────────────────────────────────────────


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    original_filename: str
    mime_type: str
    parsing_status: ParsingStatus
    extraction_confidence: float | None
    created_at: datetime


class ProcessingStatusOut(BaseModel):
    resume_id: uuid.UUID
    status: ParsingStatus
    extraction_confidence: float | None
    error_message: str | None = None


# ── Candidate ─────────────────────────────────────────────────────────────────


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    location: str | None
    summary: str | None
    created_at: datetime


# ── Application ───────────────────────────────────────────────────────────────


class ApplicationCreate(BaseModel):
    candidate_id: uuid.UUID
    job_id: uuid.UUID


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    status: ApplicationStatus
    created_at: datetime


# ── Screening ─────────────────────────────────────────────────────────────────


class ScreeningResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    overall_score: float | None
    technical_score: float | None
    experience_score: float | None
    project_score: float | None
    education_score: float | None
    domain_score: float | None
    semantic_match_score: float | None
    confidence_score: float | None
    recommendation: ScreeningRecommendation | None
    explanation: str | None
    evidence_json: dict | None
    created_at: datetime


# ── Resume Q&A ────────────────────────────────────────────────────────────────


class ResumeQARequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class ResumeQAResponse(BaseModel):
    answer: str
    evidence: list[dict[str, Any]] = []
    confidence: float | None = None
    sources: list[str] = []


# ── Interview ─────────────────────────────────────────────────────────────────


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    status: InterviewStatus
    difficulty: InterviewDifficulty
    started_at: datetime | None
    completed_at: datetime | None


class InterviewQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_number: int
    question: str
    question_type: QuestionType
    topic: str | None


class TextAnswerRequest(BaseModel):
    answer_text: str = Field(min_length=1, max_length=10_000)


class AnswerEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    correctness_score: float | None
    depth_score: float | None
    relevance_score: float | None
    clarity_score: float | None
    evaluator_confidence: float | None
    recommended_next_action: str | None


# ── Analytics ─────────────────────────────────────────────────────────────────


class RecruiterDashboardOut(BaseModel):
    active_jobs: int
    total_applicants: int
    candidates_screened: int
    candidates_awaiting_review: int
    interviews_scheduled: int
    interviews_completed: int
    recent_activity: list[dict[str, Any]] = []
