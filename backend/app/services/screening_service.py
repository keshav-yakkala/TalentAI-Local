"""
Screening Service (Phase 8)
Evidence-based candidate screening with deterministic weighted scoring.
The LLM evaluates evidence; code calculates the final weighted score.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.llms.factory import get_llm_provider
from app.ai.prompts.jd_analysis import build_skill_matching_prompt
from app.ai.structured_outputs.screening import SkillMatchResult
from app.core.config import settings
from app.core.exceptions import JobNotFoundError, ResumeNotFoundError
from app.core.logging import get_logger
from app.models.application import (
    Application,
    ApplicationStatus,
    ScreeningRecommendation,
    ScreeningResult,
)
from app.models.candidate import Candidate, Resume
from app.models.job import Job, JobRequirement

logger = get_logger(__name__)


class ScreeningService:
    """Evidence-based candidate screening with weighted scoring."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm_provider()

    async def screen_application(
        self,
        application_id: uuid.UUID,
    ) -> ScreeningResult:
        """
        Screen a candidate application against job requirements.
        Uses deterministic weighted scoring — LLM provides evidence only.
        """
        # Load application with relationships
        result = await self.db.execute(
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.candidate).selectinload(Candidate.skills),
                selectinload(Application.candidate).selectinload(Candidate.resumes),
                selectinload(Application.job).selectinload(Job.requirements),
            )
        )
        application = result.scalar_one_or_none()
        if not application:
            raise JobNotFoundError(f"Application {application_id} not found")

        candidate = application.candidate
        job = application.job

        # Get resume text
        resume = next(
            (r for r in candidate.resumes if r.raw_text), None
        )
        resume_text = resume.raw_text if resume else ""

        if not resume_text:
            raise ResumeNotFoundError("No parsed resume found for candidate")

        # Build context for LLM evaluation
        job_reqs = {
            "required_skills": [
                r.name for r in job.requirements if r.requirement_type.value == "required_skill"
            ],
            "preferred_skills": [
                r.name for r in job.requirements if r.requirement_type.value == "preferred_skill"
            ],
            "title": job.title,
            "description": job.description or "",
        }

        candidate_profile = {
            "name": candidate.full_name,
            "skills": [s.skill_name for s in candidate.skills],
            "summary": candidate.summary or "",
        }

        import json
        jd_json = json.dumps(job_reqs, indent=2)
        profile_json = json.dumps(candidate_profile, indent=2)
        resume_context = resume_text[:4000]

        prompt = build_skill_matching_prompt(jd_json, profile_json, resume_context)

        try:
            match_result: SkillMatchResult = await self.llm.structured_generate(
                prompt=prompt,
                output_schema=SkillMatchResult,
                system="You are an expert technical recruiter performing evidence-based candidate screening.",
                max_retries=3,
            )
        except Exception as exc:
            logger.error("LLM screening failed", error=str(exc))
            # Create a failed screening result with no scores
            screening = ScreeningResult(
                application_id=application_id,
                recommendation=ScreeningRecommendation.needs_human_review,
                explanation=f"AI screening failed: {exc}. Manual review required.",
            )
            self.db.add(screening)
            application.status = ApplicationStatus.human_review
            await self.db.flush()
            return screening

        # Deterministic weighted scoring
        scores = self._calculate_weighted_scores(match_result)

        # Determine recommendation
        recommendation = self._determine_recommendation(
            scores["overall"], scores["confidence"]
        )

        # Persist result
        screening = ScreeningResult(
            application_id=application_id,
            overall_score=scores["overall"],
            technical_score=scores["technical"],
            experience_score=scores["experience"],
            project_score=scores["project"],
            education_score=scores["education"],
            domain_score=scores["domain"],
            semantic_match_score=scores["semantic"],
            confidence_score=scores["confidence"],
            recommendation=recommendation,
            explanation=match_result.semantic_match_explanation,
            evidence_json={
                "required_matches": [
                    m.model_dump() for m in match_result.required_skill_matches
                ],
                "preferred_matches": [
                    m.model_dump() for m in match_result.preferred_skill_matches
                ],
                "missing_required": match_result.missing_required_skills,
                "missing_preferred": match_result.missing_preferred_skills,
            },
        )
        self.db.add(screening)

        # Update application status
        application.status = ApplicationStatus.screened
        await self.db.flush()

        logger.info(
            "Screening completed",
            application_id=str(application_id),
            overall_score=scores["overall"],
            recommendation=recommendation.value,
        )
        return screening

    def _calculate_weighted_scores(
        self, match: SkillMatchResult
    ) -> dict[str, float]:
        """
        Calculate deterministic weighted score.
        The LLM provides evidence; THIS CODE calculates the final score.
        """
        # Technical score: % of required skills found
        total_required = len(match.required_skill_matches) or 1
        found_required = sum(1 for m in match.required_skill_matches if m.found)
        technical_score = (found_required / total_required) * 100

        experience_score = match.experience_evaluation.score
        project_score = match.project_evaluation.score
        education_score = match.education_evaluation.score
        domain_score = match.domain_evaluation.score

        # Semantic match from technical score estimate
        semantic_score = min(match.technical_score, 100)

        # Weighted overall score — deterministic calculation
        overall = (
            technical_score * settings.SCREENING_WEIGHT_REQUIRED_SKILLS
            + experience_score * settings.SCREENING_WEIGHT_EXPERIENCE
            + project_score * settings.SCREENING_WEIGHT_PROJECTS
            + (found_required / total_required * 100) * settings.SCREENING_WEIGHT_PREFERRED_SKILLS
            + education_score * settings.SCREENING_WEIGHT_EDUCATION
            + domain_score * settings.SCREENING_WEIGHT_DOMAIN
            + semantic_score * settings.SCREENING_WEIGHT_SEMANTIC_MATCH
        )

        confidence = match.evaluation_confidence

        return {
            "overall": round(overall, 2),
            "technical": round(technical_score, 2),
            "experience": round(experience_score, 2),
            "project": round(project_score, 2),
            "education": round(education_score, 2),
            "domain": round(domain_score, 2),
            "semantic": round(semantic_score, 2),
            "confidence": round(confidence, 2),
        }

    def _determine_recommendation(
        self, overall_score: float, confidence: float
    ) -> ScreeningRecommendation:
        """Determine recommendation — never auto-reject."""
        if confidence < 0.4:
            return ScreeningRecommendation.needs_human_review
        if overall_score >= 75:
            return ScreeningRecommendation.strong_match
        if overall_score >= 55:
            return ScreeningRecommendation.potential_match
        if overall_score >= 35:
            return ScreeningRecommendation.needs_human_review
        return ScreeningRecommendation.weak_match
