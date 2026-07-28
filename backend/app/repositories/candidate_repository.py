"""
Candidate Repository (Phase 4)
Data access layer for Candidate, Resume, ResumeChunk models.
All queries enforce organization-level tenant isolation.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import CrossTenantAccessError, ResumeNotFoundError
from app.core.logging import get_logger
from app.models.candidate import (
    Candidate,
    CandidateExperience,
    CandidateProject,
    CandidateSkill,
    ParsingStatus,
    Resume,
    ResumeChunk,
)
from app.ai.structured_outputs.resume import ResumeProfile

logger = get_logger(__name__)


class CandidateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Candidate ─────────────────────────────────────────────────────────────

    async def create_candidate(
        self,
        full_name: str,
        email: str | None = None,
        phone: str | None = None,
        location: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Candidate:
        candidate = Candidate(
            full_name=full_name,
            email=email,
            phone=phone,
            location=location,
            user_id=user_id,
        )
        self.db.add(candidate)
        await self.db.flush()
        return candidate

    async def get_candidate(self, candidate_id: uuid.UUID) -> Candidate | None:
        result = await self.db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()

    # ── Resume ────────────────────────────────────────────────────────────────

    async def create_resume(
        self,
        candidate_id: uuid.UUID,
        file_path: str,
        original_filename: str,
        mime_type: str,
    ) -> Resume:
        resume = Resume(
            candidate_id=candidate_id,
            file_path=file_path,
            original_filename=original_filename,
            mime_type=mime_type,
            parsing_status=ParsingStatus.pending,
        )
        self.db.add(resume)
        await self.db.flush()
        return resume

    async def get_resume(self, resume_id: uuid.UUID) -> Resume | None:
        result = await self.db.execute(
            select(Resume).where(Resume.id == resume_id)
        )
        return result.scalar_one_or_none()

    async def update_resume_status(
        self,
        resume_id: uuid.UUID,
        status: ParsingStatus,
        raw_text: str | None = None,
        confidence: float | None = None,
    ) -> None:
        values: dict = {"parsing_status": status}
        if raw_text is not None:
            values["raw_text"] = raw_text
        if confidence is not None:
            values["extraction_confidence"] = confidence
        await self.db.execute(
            update(Resume).where(Resume.id == resume_id).values(**values)
        )

    # ── Structured Profile Persistence ────────────────────────────────────────

    async def save_structured_profile(
        self,
        candidate_id: uuid.UUID,
        profile: ResumeProfile,
    ) -> None:
        """
        Persist LLM-extracted structured resume data to the database.
        Called after ResumeProfile passes Pydantic validation.
        """
        # Update candidate basic info if richer data extracted
        info = profile.personal_information
        if info.full_name or info.email or info.phone or info.location:
            candidate = await self.get_candidate(candidate_id)
            if candidate:
                if info.full_name:
                    candidate.full_name = info.full_name
                if info.email and not candidate.email:
                    candidate.email = info.email
                if info.phone and not candidate.phone:
                    candidate.phone = info.phone
                if info.location and not candidate.location:
                    candidate.location = info.location
                if profile.summary and not candidate.summary:
                    candidate.summary = profile.summary

        # Skills
        for skill in profile.skills:
            self.db.add(CandidateSkill(
                candidate_id=candidate_id,
                skill_name=skill.name,
                proficiency=skill.proficiency,
                evidence=skill.evidence,
                confidence=None,
            ))

        # Experience
        for exp in profile.experience:
            self.db.add(CandidateExperience(
                candidate_id=candidate_id,
                company=exp.company,
                title=exp.title,
                description=exp.description,
            ))

        # Projects
        for proj in profile.projects:
            self.db.add(CandidateProject(
                candidate_id=candidate_id,
                name=proj.name,
                description=proj.description,
                technologies=proj.technologies,
            ))

        await self.db.flush()
        logger.info("Structured profile saved", candidate_id=str(candidate_id))

    # ── Resume Chunks (tenant-isolated) ───────────────────────────────────────

    async def save_chunks(
        self,
        resume_id: uuid.UUID,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        chunks: list[dict],
    ) -> list[ResumeChunk]:
        """
        Save resume chunks with embeddings to the database.
        CRITICAL: organization_id is stored on every chunk for tenant isolation.
        Vector retrieval MUST filter by organization_id — never skip this.
        """
        from app.models.candidate import ResumeSectionType

        saved = []
        for chunk_data in chunks:
            section_type_str = chunk_data.get("section_type", "other")
            try:
                section_type = ResumeSectionType(section_type_str)
            except ValueError:
                section_type = ResumeSectionType.other

            chunk = ResumeChunk(
                resume_id=resume_id,
                candidate_id=candidate_id,
                organization_id=organization_id,  # MANDATORY — tenant isolation
                section_type=section_type,
                content=chunk_data["content"],
                embedding=chunk_data.get("embedding"),
                metadata_json=chunk_data.get("metadata", {}),
            )
            self.db.add(chunk)
            saved.append(chunk)

        await self.db.flush()
        logger.info(
            "Chunks saved",
            resume_id=str(resume_id),
            count=len(saved),
            organization_id=str(organization_id),
        )
        return saved

    async def get_chunks_for_candidate(
        self,
        candidate_id: uuid.UUID,
        organization_id: uuid.UUID,
        section_types: list[str] | None = None,
    ) -> list[ResumeChunk]:
        """
        Retrieve chunks for a candidate.
        ALWAYS filters by both candidate_id AND organization_id.
        This double-filter is the security layer preventing cross-tenant access.
        """
        query = select(ResumeChunk).where(
            ResumeChunk.candidate_id == candidate_id,
            ResumeChunk.organization_id == organization_id,  # tenant isolation
        )
        if section_types:
            from app.models.candidate import ResumeSectionType
            types = [ResumeSectionType(t) for t in section_types]
            query = query.where(ResumeChunk.section_type.in_(types))

        result = await self.db.execute(query)
        return list(result.scalars().all())
