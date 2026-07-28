"""Job and JobRequirement models."""
import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class JobStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    closed = "closed"
    archived = "archived"


class EmploymentType(str, enum.Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"
    freelance = "freelance"


class RequirementType(str, enum.Enum):
    required_skill = "required_skill"
    preferred_skill = "preferred_skill"
    experience = "experience"
    education = "education"
    certification = "certification"
    domain = "domain"


class RequirementImportance(str, enum.Enum):
    must_have = "must_have"
    nice_to_have = "nice_to_have"


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(String(128))
    location: Mapped[str | None] = mapped_column(String(256))
    employment_type: Mapped[EmploymentType | None] = mapped_column(
        Enum(EmploymentType, name="employment_type")
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), nullable=False, default=JobStatus.draft
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="jobs")
    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="job")


class JobRequirement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "job_requirements"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType, name="requirement_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    importance: Mapped[RequirementImportance] = mapped_column(
        Enum(RequirementImportance, name="requirement_importance"),
        nullable=False,
        default=RequirementImportance.must_have,
    )
    weight: Mapped[float | None] = mapped_column(Float)
    minimum_level: Mapped[str | None] = mapped_column(String(64))

    # Relationship
    job: Mapped["Job"] = relationship(back_populates="requirements")
