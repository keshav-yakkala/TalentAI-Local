"""
JD Analysis Service (Phase 6)
Replaces hardcoded ROLE_REQUIREMENTS dict from app.py with
AI-powered structured extraction stored in the database.

Original app.py had:
    ROLE_REQUIREMENTS = {
        "Software Engineer": {"Python": 8, "Java": 6, ...},
        ...
    }
This was fixed, inflexible, and required code changes to add new roles.

This service:
1. Accepts free-form JD text
2. Extracts structured requirements via LLM + Pydantic validation
3. Persists to JobRequirement table
4. Supports any role/technology — not limited to hardcoded list
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llms.factory import get_llm_provider
from app.ai.prompts.jd_analysis import build_jd_analysis_prompt
from app.ai.structured_outputs.screening import JDAnalysis
from app.core.exceptions import LLMOutputValidationError
from app.core.logging import get_logger
from app.models.job import Job, JobRequirement, RequirementImportance, RequirementType

logger = get_logger(__name__)


class JDAnalysisService:
    """Analyze JD text and extract structured requirements."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm_provider()

    async def analyze_and_save(
        self,
        job_id: uuid.UUID,
        jd_text: str,
        replace_existing: bool = False,
    ) -> JDAnalysis:
        """
        Analyze JD text, extract requirements, and persist to DB.
        
        Args:
            job_id: The job to attach requirements to
            jd_text: Raw job description text
            replace_existing: If True, delete existing requirements first
            
        Returns:
            Validated JDAnalysis Pydantic model
        """
        logger.info("Analyzing JD", job_id=str(job_id), jd_length=len(jd_text))

        # LLM extraction with Pydantic validation (no eval, no regex)
        prompt = build_jd_analysis_prompt(jd_text)
        analysis: JDAnalysis = await self.llm.structured_generate(
            prompt=prompt,
            output_schema=JDAnalysis,
            system="You are a technical recruiter assistant that extracts structured job requirements from job descriptions.",
            max_retries=3,
        )

        # Persist to database
        if replace_existing:
            from sqlalchemy import delete
            await self.db.execute(
                delete(JobRequirement).where(JobRequirement.job_id == job_id)
            )

        # Required skills
        for skill in analysis.required_skills:
            self.db.add(JobRequirement(
                job_id=job_id,
                requirement_type=RequirementType.required_skill,
                name=skill.name,
                importance=RequirementImportance.must_have,
                weight=0.30 / max(len(analysis.required_skills), 1),
            ))

        # Preferred skills
        for skill in analysis.preferred_skills:
            self.db.add(JobRequirement(
                job_id=job_id,
                requirement_type=RequirementType.preferred_skill,
                name=skill.name,
                importance=RequirementImportance.nice_to_have,
                weight=0.10 / max(len(analysis.preferred_skills), 1),
            ))

        # Experience requirement
        if analysis.min_years_experience:
            self.db.add(JobRequirement(
                job_id=job_id,
                requirement_type=RequirementType.experience,
                name=f"Minimum {analysis.min_years_experience} years experience",
                importance=RequirementImportance.must_have,
                minimum_level=str(analysis.min_years_experience),
            ))

        # Education
        if analysis.education_requirement:
            self.db.add(JobRequirement(
                job_id=job_id,
                requirement_type=RequirementType.education,
                name=analysis.education_requirement,
                importance=RequirementImportance.must_have,
            ))

        # Domain knowledge
        for domain in analysis.domain_knowledge:
            self.db.add(JobRequirement(
                job_id=job_id,
                requirement_type=RequirementType.domain,
                name=domain,
                importance=RequirementImportance.nice_to_have,
            ))

        await self.db.flush()
        logger.info(
            "JD analysis saved",
            job_id=str(job_id),
            required_skills=len(analysis.required_skills),
            preferred_skills=len(analysis.preferred_skills),
            confidence=analysis.extraction_confidence,
        )
        return analysis
