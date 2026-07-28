"""Application, ScreeningResult, Interview, InterviewQuestion, InterviewAnswer,
AnswerEvaluation, FinalInterviewReport models."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationStatus(str, enum.Enum):
    applied = "applied"
    processing = "processing"
    screened = "screened"
    human_review = "human_review"
    shortlisted = "shortlisted"
    interview_invited = "interview_invited"
    interviewing = "interviewing"
    interview_completed = "interview_completed"
    final_review = "final_review"
    selected = "selected"
    rejected = "rejected"


class ScreeningRecommendation(str, enum.Enum):
    strong_match = "strong_match"
    potential_match = "potential_match"
    needs_human_review = "needs_human_review"
    weak_match = "weak_match"


class InterviewStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class InterviewDifficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"
    adaptive = "adaptive"


class QuestionType(str, enum.Enum):
    resume_based = "resume_based"
    project_deep_dive = "project_deep_dive"
    technical_fundamentals = "technical_fundamentals"
    system_design = "system_design"
    scenario_based = "scenario_based"
    debugging = "debugging"
    behavioral = "behavioral"
    follow_up = "follow_up"
    clarification = "clarification"


class Application(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "applications"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.applied,
    )

    # Relationships
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")
    job: Mapped["Job"] = relationship(back_populates="applications")
    screening_result: Mapped["ScreeningResult | None"] = relationship(
        back_populates="application", uselist=False
    )
    interview: Mapped["Interview | None"] = relationship(
        back_populates="application", uselist=False
    )


class ScreeningResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "screening_results"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    overall_score: Mapped[float | None] = mapped_column(Float)
    technical_score: Mapped[float | None] = mapped_column(Float)
    experience_score: Mapped[float | None] = mapped_column(Float)
    project_score: Mapped[float | None] = mapped_column(Float)
    education_score: Mapped[float | None] = mapped_column(Float)
    domain_score: Mapped[float | None] = mapped_column(Float)
    semantic_match_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    recommendation: Mapped[ScreeningRecommendation | None] = mapped_column(
        Enum(ScreeningRecommendation, name="screening_recommendation")
    )
    explanation: Mapped[str | None] = mapped_column(Text)
    evidence_json: Mapped[dict | None] = mapped_column(JSON)

    application: Mapped["Application"] = relationship(back_populates="screening_result")


class Interview(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status"),
        nullable=False,
        default=InterviewStatus.pending,
    )
    current_stage: Mapped[str | None] = mapped_column(String(128))
    difficulty: Mapped[InterviewDifficulty] = mapped_column(
        Enum(InterviewDifficulty, name="interview_difficulty"),
        nullable=False,
        default=InterviewDifficulty.adaptive,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application: Mapped["Application"] = relationship(back_populates="interview")
    questions: Mapped[list["InterviewQuestion"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan", order_by="InterviewQuestion.sequence_number"
    )
    report: Mapped["FinalInterviewReport | None"] = relationship(
        back_populates="interview", uselist=False
    )


class InterviewQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_questions"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"), nullable=False
    )
    topic: Mapped[str | None] = mapped_column(String(128))
    difficulty: Mapped[str | None] = mapped_column(String(32))
    reason_for_question: Mapped[str | None] = mapped_column(Text)
    source_context_json: Mapped[dict | None] = mapped_column(JSON)

    interview: Mapped["Interview"] = relationship(back_populates="questions")
    answer: Mapped["InterviewAnswer | None"] = relationship(
        back_populates="question", uselist=False
    )


class InterviewAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "interview_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(String(512))
    transcription: Mapped[str | None] = mapped_column(Text)

    question: Mapped["InterviewQuestion"] = relationship(back_populates="answer")
    evaluation: Mapped["AnswerEvaluation | None"] = relationship(
        back_populates="answer", uselist=False
    )


class AnswerEvaluation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "answer_evaluations"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interview_answers.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    correctness_score: Mapped[float | None] = mapped_column(Float)
    depth_score: Mapped[float | None] = mapped_column(Float)
    relevance_score: Mapped[float | None] = mapped_column(Float)
    clarity_score: Mapped[float | None] = mapped_column(Float)
    practical_understanding_score: Mapped[float | None] = mapped_column(Float)
    evaluator_confidence: Mapped[float | None] = mapped_column(Float)
    strengths: Mapped[list[str] | None] = mapped_column(JSON)
    weaknesses: Mapped[list[str] | None] = mapped_column(JSON)
    missing_concepts: Mapped[list[str] | None] = mapped_column(JSON)
    recommended_next_action: Mapped[str | None] = mapped_column(String(64))

    answer: Mapped["InterviewAnswer"] = relationship(back_populates="evaluation")


class FinalInterviewReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "final_interview_reports"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    technical_score: Mapped[float | None] = mapped_column(Float)
    communication_score: Mapped[float | None] = mapped_column(Float)
    problem_solving_score: Mapped[float | None] = mapped_column(Float)
    consistency_score: Mapped[float | None] = mapped_column(Float)
    strengths: Mapped[list[str] | None] = mapped_column(JSON)
    weaknesses: Mapped[list[str] | None] = mapped_column(JSON)
    skill_gaps: Mapped[list[str] | None] = mapped_column(JSON)
    recommendation: Mapped[ScreeningRecommendation | None] = mapped_column(
        Enum(ScreeningRecommendation, name="screening_recommendation")
    )
    confidence: Mapped[float | None] = mapped_column(Float)
    recruiter_notes: Mapped[str | None] = mapped_column(Text)

    interview: Mapped["Interview"] = relationship(back_populates="report")
