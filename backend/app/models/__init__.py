"""
Model registry — import all models here so Alembic autogenerate
discovers every table when it imports this module.
"""
from app.db.base import Base  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.organization import Organization, OrganizationMember, OrgMemberRole  # noqa: F401
from app.models.job import Job, JobRequirement, JobStatus, EmploymentType, RequirementType  # noqa: F401
from app.models.candidate import (  # noqa: F401
    Candidate,
    Resume,
    ResumeChunk,
    CandidateSkill,
    CandidateExperience,
    CandidateProject,
    ParsingStatus,
    ResumeSectionType,
)
from app.models.application import (  # noqa: F401
    Application,
    ScreeningResult,
    Interview,
    InterviewQuestion,
    InterviewAnswer,
    AnswerEvaluation,
    FinalInterviewReport,
    ApplicationStatus,
    InterviewStatus,
    QuestionType,
)
from app.models.audit import AuditLog, WorkflowRun, WorkflowType, WorkflowStatus  # noqa: F401
