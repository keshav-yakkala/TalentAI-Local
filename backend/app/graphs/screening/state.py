"""
Candidate Screening LangGraph — State
"""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.ai.structured_outputs.screening import JDAnalysis, SkillMatchResult


class ScreeningState(BaseModel):
    """State for the candidate screening workflow."""

    # Identifiers
    workflow_id: str
    application_id: str
    candidate_id: str
    job_id: str
    organization_id: str

    # Input data
    jd_analysis: JDAnalysis | None = None
    resume_profile_json: str | None = None
    retrieved_chunks: list[dict[str, Any]] = Field(default_factory=list)

    # Scoring dimensions (0-100 each)
    required_skills_score: float = 0.0
    preferred_skills_score: float = 0.0
    experience_score: float = 0.0
    project_score: float = 0.0
    education_score: float = 0.0
    domain_score: float = 0.0
    semantic_match_score: float = 0.0

    # Evidence
    skill_match_result: SkillMatchResult | None = None
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    missing_required_skills: list[str] = Field(default_factory=list)

    # Overall
    overall_score: float = 0.0
    confidence_score: float = 0.0
    recommendation: str | None = None  # strong_match|potential_match|needs_human_review|weak_match
    explanation: str | None = None

    # Control flow
    current_status: str = "pending"
    requires_human_review: bool = False
    human_review_reason: str | None = None
    errors: list[str] = Field(default_factory=list)
