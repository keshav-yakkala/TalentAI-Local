"""
Pydantic v2 structured output schemas for LLM responses.
Every LLM interaction that produces structured data must validate through these schemas.
NEVER parse LLM output with regex or eval() for important data.

Resume extraction schemas — migrated from unvalidated dict parsing in agents.py.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


class SkillEntry(BaseModel):
    name: str
    proficiency: str | None = None  # e.g., "advanced", "intermediate", "beginner"
    years_of_experience: float | None = None
    evidence: str | None = None  # Quote from resume that proves this skill


class ExperienceEntry(BaseModel):
    company: str | None = None
    title: str | None = None
    start_date: str | None = None  # ISO string or natural language "Jan 2022"
    end_date: str | None = None   # or "Present"
    duration_months: int | None = None
    description: str | None = None
    key_achievements: list[str] = []
    technologies_used: list[str] = []


class EducationEntry(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    graduation_year: int | None = None
    gpa: float | None = None


class ProjectEntry(BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] = []
    role: str | None = None
    impact: str | None = None
    url: str | None = None


class CertificationEntry(BaseModel):
    name: str
    issuer: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None


class ResearchEntry(BaseModel):
    title: str
    publication: str | None = None
    year: int | None = None
    description: str | None = None


class AchievementEntry(BaseModel):
    title: str
    description: str | None = None
    metric: str | None = None  # e.g., "Reduced latency by 40%"


class PersonalInformation(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ResumeProfile(BaseModel):
    """
    Complete structured representation of a resume.
    Extracted by LLM and validated by Pydantic before storage.
    """

    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    summary: str | None = None
    skills: list[SkillEntry] = []
    experience: list[ExperienceEntry] = []
    education: list[EducationEntry] = []
    projects: list[ProjectEntry] = []
    certifications: list[CertificationEntry] = []
    research: list[ResearchEntry] = []
    achievements: list[AchievementEntry] = []

    # Extraction metadata
    extraction_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    extraction_notes: str | None = None  # Any caveats or issues the LLM noticed

    def total_years_experience(self) -> float:
        """Calculate total work experience in years from parsed entries."""
        total_months = sum(
            exp.duration_months or 0 for exp in self.experience
        )
        return round(total_months / 12, 1)

    def get_all_skill_names(self) -> list[str]:
        """Return normalized list of all skill names."""
        return [s.name.strip() for s in self.skills if s.name]
