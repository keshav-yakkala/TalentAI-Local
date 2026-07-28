"""
Structured output schemas for JD analysis, candidate screening, and answer evaluation.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


# ── JD Analysis ───────────────────────────────────────────────────────────────


class ExtractedSkill(BaseModel):
    name: str
    importance: Literal["required", "preferred"] = "required"
    context: str | None = None  # How this skill was mentioned in the JD


class JDAnalysis(BaseModel):
    """
    Structured extraction of a job description.
    Replaces hardcoded ROLE_REQUIREMENTS in app.py.
    """

    job_title: str | None = None
    seniority_level: str | None = None  # e.g., "senior", "mid-level", "junior"
    required_skills: list[ExtractedSkill] = []
    preferred_skills: list[ExtractedSkill] = []
    responsibilities: list[str] = []
    min_years_experience: float | None = None
    education_requirement: str | None = None
    certifications: list[str] = []
    domain_knowledge: list[str] = []
    soft_skills: list[str] = []
    extraction_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0


# ── Screening ─────────────────────────────────────────────────────────────────


class SkillMatchEvidence(BaseModel):
    skill_name: str
    found: bool
    evidence: str | None = None  # Exact quote from resume proving this skill
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    proficiency_level: str | None = None


class CategoryScore(BaseModel):
    score: Annotated[float, Field(ge=0.0, le=100.0)]
    evidence: list[str] = []
    explanation: str
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0


class SkillMatchResult(BaseModel):
    """
    Evidence-based skill matching result.
    The LLM provides evidence; deterministic code calculates the weighted final score.
    """

    required_skill_matches: list[SkillMatchEvidence] = []
    preferred_skill_matches: list[SkillMatchEvidence] = []
    experience_evaluation: CategoryScore
    project_evaluation: CategoryScore
    education_evaluation: CategoryScore
    domain_evaluation: CategoryScore
    technical_score: Annotated[float, Field(ge=0.0, le=100.0)]  # LLM assessment
    semantic_match_explanation: str
    missing_required_skills: list[str] = []
    missing_preferred_skills: list[str] = []
    evaluation_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0


# ── Interview ─────────────────────────────────────────────────────────────────


class InterviewQuestionOutput(BaseModel):
    """Single generated interview question with full context."""

    question: str
    topic: str
    question_type: str  # maps to QuestionType enum
    difficulty: Literal["easy", "medium", "hard"]
    reason_for_question: str
    resume_evidence_references: list[str] = []
    job_requirement_references: list[str] = []


class AnswerEvaluationOutput(BaseModel):
    """
    Multi-dimensional evaluation of a candidate's interview answer.
    Replaces binary yes/no evaluation from original ui.py.
    """

    correctness_score: Annotated[float, Field(ge=0.0, le=10.0)]
    depth_score: Annotated[float, Field(ge=0.0, le=10.0)]
    relevance_score: Annotated[float, Field(ge=0.0, le=10.0)]
    clarity_score: Annotated[float, Field(ge=0.0, le=10.0)]
    practical_understanding_score: Annotated[float, Field(ge=0.0, le=10.0)]
    evaluator_confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    strengths: list[str] = []
    missing_concepts: list[str] = []
    incorrect_claims: list[str] = []
    suggested_follow_up: str | None = None
    recommended_next_action: Literal[
        "deeper_question",
        "clarification",
        "increase_difficulty",
        "decrease_difficulty",
        "change_topic",
        "continue",
        "finish_interview",
    ]


# ── Resume Improvement ────────────────────────────────────────────────────────


class BulletImprovement(BaseModel):
    original: str
    improved: str
    reason: str
    is_fabricated: bool = False  # Must always be False — never invent data

    def model_post_init(self, __context: object) -> None:
        if self.is_fabricated:
            raise ValueError(
                "BulletImprovement.is_fabricated must never be True. "
                "Do not fabricate experience, metrics, or achievements."
            )


class ResumeImprovementOutput(BaseModel):
    """
    Safe resume improvement suggestions.
    CRITICAL: Must not fabricate companies, projects, skills, or metrics.
    All improvements must be based on verified candidate information.
    """

    weak_bullets_identified: list[str] = []
    improved_bullets: list[BulletImprovement] = []
    missing_measurable_impact: list[str] = []  # Suggestions, not inventions
    suggested_action_verbs: list[str] = []
    ats_keywords_to_add: list[str] = []  # Only skills the candidate actually has evidence for
    overall_assessment: str
    safety_note: str = (
        "All suggestions are based on verified resume content. "
        "Metrics marked as 'Add a real metric here' require actual data from the candidate."
    )
