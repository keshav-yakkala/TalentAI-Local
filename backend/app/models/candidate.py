"""
Candidate, Resume, ResumeChunk, and derived profile models.
pgvector is used for the ResumeChunk.embedding column.
"""
import enum
import uuid
from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ParsingStatus(str, enum.Enum):
    pending = "pending"
    parsing = "parsing"
    extracting = "extracting"
    embedding = "embedding"
    completed = "completed"
    failed = "failed"
    human_review_required = "human_review_required"


class ResumeSectionType(str, enum.Enum):
    profile_summary = "profile_summary"
    skills = "skills"
    experience = "experience"
    project = "project"
    education = "education"
    certification = "certification"
    research = "research"
    achievement = "achievement"
    other = "other"


class Candidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidates"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(256))
    summary: Mapped[str | None] = mapped_column(Text)

    # Relationships
    user: Mapped["User | None"] = relationship(back_populates="candidate_profile")
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    skills: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    experiences: Mapped[list["CandidateExperience"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    projects: Mapped[list["CandidateProject"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="candidate")


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resumes"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        Enum(ParsingStatus, name="parsing_status"),
        nullable=False,
        default=ParsingStatus.pending,
    )
    extraction_confidence: Mapped[float | None] = mapped_column(Float)

    # Relationships
    candidate: Mapped["Candidate"] = relationship(back_populates="resumes")
    chunks: Mapped[list["ResumeChunk"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )


class ResumeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A semantic section of a resume stored with its embedding for vector search.
    CRITICAL: Every retrieval query MUST filter by organization_id AND candidate_id
    to enforce multi-tenant isolation. Never rely on prompt instructions for security.
    """

    __tablename__ = "resume_chunks"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_type: Mapped[ResumeSectionType] = mapped_column(
        Enum(ResumeSectionType, name="resume_section_type"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # pgvector column — dimension must match EMBEDDING_DIMENSION setting
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSION)
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    # Relationships
    resume: Mapped["Resume"] = relationship(back_populates="chunks")


class CandidateSkill(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "candidate_skills"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    skill_name: Mapped[str] = mapped_column(String(128), nullable=False)
    proficiency: Mapped[str | None] = mapped_column(String(32))  # beginner/intermediate/advanced/expert
    evidence: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)

    candidate: Mapped["Candidate"] = relationship(back_populates="skills")


class CandidateExperience(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "candidate_experiences"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    company: Mapped[str | None] = mapped_column(String(256))
    title: Mapped[str | None] = mapped_column(String(256))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped["Candidate"] = relationship(back_populates="experiences")


class CandidateProject(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "candidate_projects"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list[str] | None] = mapped_column(JSON)
    evidence: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped["Candidate"] = relationship(back_populates="projects")
