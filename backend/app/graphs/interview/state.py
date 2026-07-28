"""
Adaptive Interview LangGraph — State
Tracks the full conversation history, difficulty adaptation, and evaluation.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.ai.structured_outputs.screening import AnswerEvaluationOutput, InterviewQuestionOutput


class QuestionRecord(BaseModel):
    """A single Q&A exchange in the interview."""
    sequence_number: int
    question: str
    question_type: str
    topic: str | None = None
    difficulty: str = "medium"
    answer_text: str | None = None
    transcription: str | None = None  # Whisper output
    evaluation: AnswerEvaluationOutput | None = None


class InterviewPlan(BaseModel):
    """High-level interview structure planned at the start."""
    topics_to_cover: list[str] = Field(default_factory=list)
    resume_weak_spots: list[str] = Field(default_factory=list)
    key_required_skills: list[str] = Field(default_factory=list)
    estimated_question_count: int = 8


class AdaptiveInterviewState(BaseModel):
    """Full state of an adaptive interview session."""

    # Identifiers
    workflow_id: str
    interview_id: str
    application_id: str
    candidate_id: str
    organization_id: str

    # Context (loaded at start)
    resume_profile_json: str | None = None
    jd_analysis_json: str | None = None
    interview_plan: InterviewPlan | None = None

    # Interview history
    questions: list[QuestionRecord] = Field(default_factory=list)
    current_question_number: int = 0
    max_questions: int = 10

    # Difficulty tracking
    current_difficulty: Literal["easy", "medium", "hard"] = "medium"
    consecutive_strong: int = 0   # Strong answers → increase difficulty
    consecutive_weak: int = 0     # Weak answers → decrease difficulty / clarify
    topics_covered: list[str] = Field(default_factory=list)
    topics_remaining: list[str] = Field(default_factory=list)

    # Current turn
    current_question: InterviewQuestionOutput | None = None
    waiting_for_answer: bool = False
    pending_audio_path: str | None = None

    # Scoring accumulators
    cumulative_scores: dict[str, list[float]] = Field(default_factory=lambda: {
        "correctness": [], "depth": [], "relevance": [], "clarity": [], "practical": []
    })

    # Final report
    final_report_generated: bool = False
    technical_score: float | None = None
    communication_score: float | None = None
    problem_solving_score: float | None = None

    # Control flow
    current_status: str = "pending"  # pending|planning|questioning|evaluating|completed|failed
    next_action: str | None = None   # generate_question|follow_up|clarification|finish
    errors: list[str] = Field(default_factory=list)

    def current_avg_score(self) -> float:
        """Calculate running average across all dimensions."""
        all_scores = []
        for scores in self.cumulative_scores.values():
            all_scores.extend(scores)
        return sum(all_scores) / len(all_scores) if all_scores else 5.0

    def interview_complete(self) -> bool:
        return (
            self.current_question_number >= self.max_questions
            or not self.topics_remaining
        )
