"""
Interview Service (Phase 9)
Manages adaptive AI interviews with stateful question generation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.llms.factory import get_llm_provider
from app.ai.structured_outputs.screening import (
    AnswerEvaluationOutput,
    InterviewQuestionOutput,
)
from app.core.exceptions import InterviewNotFoundError
from app.core.logging import get_logger
from app.models.application import (
    AnswerEvaluation,
    Application,
    ApplicationStatus,
    Interview,
    InterviewAnswer,
    InterviewDifficulty,
    InterviewQuestion,
    InterviewStatus,
    QuestionType,
)
from app.models.candidate import Candidate

logger = get_logger(__name__)

MAX_QUESTIONS = 10
MAX_FOLLOW_UPS = 2


class InterviewService:
    """Manages adaptive AI interviews."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm_provider()

    async def create_interview(
        self,
        application_id: uuid.UUID,
        difficulty: InterviewDifficulty = InterviewDifficulty.adaptive,
    ) -> Interview:
        """Create a new interview for an application."""
        interview = Interview(
            application_id=application_id,
            status=InterviewStatus.pending,
            difficulty=difficulty,
        )
        self.db.add(interview)
        await self.db.flush()

        # Update application status
        result = await self.db.execute(
            select(Application).where(Application.id == application_id)
        )
        app = result.scalar_one_or_none()
        if app:
            app.status = ApplicationStatus.interview_invited

        logger.info("Interview created", interview_id=str(interview.id))
        return interview

    async def start_interview(self, interview_id: uuid.UUID) -> Interview:
        """Start an interview and generate the first question."""
        interview = await self._get_interview(interview_id)
        interview.status = InterviewStatus.in_progress
        interview.started_at = datetime.now(UTC)

        # Update application status
        result = await self.db.execute(
            select(Application).where(Application.id == interview.application_id)
        )
        app = result.scalar_one_or_none()
        if app:
            app.status = ApplicationStatus.interviewing

        await self.db.flush()

        # Generate first question
        await self._generate_next_question(interview)
        return interview

    async def get_current_question(
        self, interview_id: uuid.UUID
    ) -> InterviewQuestion | None:
        """Get the latest unanswered question."""
        result = await self.db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.interview_id == interview_id)
            .outerjoin(InterviewAnswer)
            .where(InterviewAnswer.id.is_(None))
            .order_by(InterviewQuestion.sequence_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def submit_text_answer(
        self,
        interview_id: uuid.UUID,
        answer_text: str,
    ) -> dict:
        """Submit a text answer, evaluate it, and generate next question."""
        interview = await self._get_interview(interview_id)

        if interview.status != InterviewStatus.in_progress:
            raise InterviewNotFoundError("Interview is not in progress")

        # Get current unanswered question
        question = await self.get_current_question(interview_id)
        if not question:
            raise InterviewNotFoundError("No pending question found")

        # Save answer
        answer = InterviewAnswer(
            question_id=question.id,
            answer_text=answer_text,
        )
        self.db.add(answer)
        await self.db.flush()

        # Evaluate answer
        evaluation = await self._evaluate_answer(question, answer)

        # Check if interview should end
        question_count = await self._get_question_count(interview_id)
        should_finish = (
            question_count >= MAX_QUESTIONS
            or evaluation.recommended_next_action == "finish_interview"
        )

        if should_finish:
            interview.status = InterviewStatus.completed
            interview.completed_at = datetime.now(UTC)

            result = await self.db.execute(
                select(Application).where(Application.id == interview.application_id)
            )
            app = result.scalar_one_or_none()
            if app:
                app.status = ApplicationStatus.interview_completed
        else:
            # Generate next question
            await self._generate_next_question(interview, evaluation)

        await self.db.flush()

        return {
            "evaluation": {
                "correctness": evaluation.correctness_score,
                "depth": evaluation.depth_score,
                "relevance": evaluation.relevance_score,
                "clarity": evaluation.clarity_score,
            },
            "interview_status": interview.status.value,
            "questions_answered": question_count,
            "max_questions": MAX_QUESTIONS,
        }

    async def get_interview_report(
        self, interview_id: uuid.UUID
    ) -> dict:
        """Get interview results summary."""
        interview = await self._get_interview(interview_id)

        result = await self.db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.interview_id == interview_id)
            .options(
                selectinload(InterviewQuestion.answer).selectinload(
                    InterviewAnswer.evaluation
                )
            )
            .order_by(InterviewQuestion.sequence_number)
        )
        questions = result.scalars().all()

        qa_pairs = []
        total_scores = {"correctness": 0, "depth": 0, "relevance": 0, "clarity": 0}
        evaluated_count = 0

        for q in questions:
            entry = {
                "question": q.question,
                "topic": q.topic,
                "type": q.question_type.value,
                "answer": q.answer.answer_text if q.answer else None,
                "evaluation": None,
            }
            if q.answer and q.answer.evaluation:
                ev = q.answer.evaluation
                entry["evaluation"] = {
                    "correctness": ev.correctness_score,
                    "depth": ev.depth_score,
                    "relevance": ev.relevance_score,
                    "clarity": ev.clarity_score,
                    "strengths": ev.strengths or [],
                    "weaknesses": ev.weaknesses or [],
                }
                total_scores["correctness"] += ev.correctness_score or 0
                total_scores["depth"] += ev.depth_score or 0
                total_scores["relevance"] += ev.relevance_score or 0
                total_scores["clarity"] += ev.clarity_score or 0
                evaluated_count += 1
            qa_pairs.append(entry)

        avg_scores = {
            k: round(v / max(evaluated_count, 1), 1)
            for k, v in total_scores.items()
        }

        return {
            "interview_id": str(interview.id),
            "status": interview.status.value,
            "started_at": interview.started_at.isoformat() if interview.started_at else None,
            "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
            "total_questions": len(questions),
            "average_scores": avg_scores,
            "questions_and_answers": qa_pairs,
        }

    async def _get_interview(self, interview_id: uuid.UUID) -> Interview:
        result = await self.db.execute(
            select(Interview).where(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        if not interview:
            raise InterviewNotFoundError(f"Interview {interview_id} not found")
        return interview

    async def _get_question_count(self, interview_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(InterviewQuestion.id)).where(
                InterviewQuestion.interview_id == interview_id
            )
        )
        return result.scalar() or 0

    async def _generate_next_question(
        self,
        interview: Interview,
        prev_evaluation: AnswerEvaluationOutput | None = None,
    ) -> InterviewQuestion:
        """Generate the next adaptive interview question."""
        question_count = await self._get_question_count(interview.id)

        # Build context for question generation
        result = await self.db.execute(
            select(Application)
            .where(Application.id == interview.application_id)
            .options(
                selectinload(Application.candidate),
                selectinload(Application.job),
            )
        )
        app = result.scalar_one()

        # Get previous questions to avoid repetition
        prev_result = await self.db.execute(
            select(InterviewQuestion)
            .where(InterviewQuestion.interview_id == interview.id)
            .order_by(InterviewQuestion.sequence_number)
        )
        previous_questions = [q.question for q in prev_result.scalars().all()]

        difficulty = "medium"
        if prev_evaluation:
            avg = (
                prev_evaluation.correctness_score
                + prev_evaluation.depth_score
                + prev_evaluation.relevance_score
            ) / 3
            if avg >= 7:
                difficulty = "hard"
            elif avg <= 4:
                difficulty = "easy"

        prompt = f"""Generate the next interview question for this candidate.

Job: {app.job.title}
Job Description: {(app.job.description or "")[:1000]}
Candidate: {app.candidate.full_name}
Candidate Summary: {(app.candidate.summary or "")[:500]}
Question Number: {question_count + 1} of {MAX_QUESTIONS}
Difficulty: {difficulty}
Previous Questions (DO NOT REPEAT): {previous_questions}
{"Previous answer evaluation: " + prev_evaluation.recommended_next_action if prev_evaluation else "This is the first question."}

Generate exactly ONE question that:
1. Is relevant to the job requirements
2. Is NOT semantically similar to any previous question
3. Matches the specified difficulty level
4. Tests the candidate's real-world understanding"""

        try:
            output: InterviewQuestionOutput = await self.llm.structured_generate(
                prompt=prompt,
                output_schema=InterviewQuestionOutput,
                system="You are a technical interviewer generating focused, relevant interview questions.",
                max_retries=2,
            )

            # Map question_type string to enum
            try:
                q_type = QuestionType(output.question_type)
            except ValueError:
                q_type = QuestionType.technical_fundamentals

            question = InterviewQuestion(
                interview_id=interview.id,
                sequence_number=question_count + 1,
                question=output.question,
                question_type=q_type,
                topic=output.topic,
                difficulty=output.difficulty,
                reason_for_question=output.reason_for_question,
            )
        except Exception as exc:
            logger.warning("Question generation failed, using fallback", error=str(exc))
            question = InterviewQuestion(
                interview_id=interview.id,
                sequence_number=question_count + 1,
                question=f"Tell me about your experience relevant to the {app.job.title} role.",
                question_type=QuestionType.behavioral,
                topic="general",
                difficulty="medium",
                reason_for_question="Fallback question due to generation error",
            )

        self.db.add(question)
        await self.db.flush()
        return question

    async def _evaluate_answer(
        self,
        question: InterviewQuestion,
        answer: InterviewAnswer,
    ) -> AnswerEvaluationOutput:
        """Evaluate a candidate's answer using structured LLM output."""
        prompt = f"""Evaluate this interview answer.

Question: {question.question}
Topic: {question.topic or "general"}
Difficulty: {question.difficulty or "medium"}

Candidate's Answer:
{answer.answer_text}

Evaluate on these dimensions (0-10):
- correctness_score: Is the answer factually correct?
- depth_score: Does the answer show deep understanding?
- relevance_score: Does it directly address the question?
- clarity_score: Is the answer well-structured and clear?
- practical_understanding_score: Does it show real-world experience?

Also provide:
- evaluator_confidence: Your confidence in this evaluation (0-1)
- strengths: What was good about the answer
- missing_concepts: What important concepts were missed
- incorrect_claims: Any factually wrong statements
- recommended_next_action: What should happen next in the interview"""

        try:
            eval_output: AnswerEvaluationOutput = await self.llm.structured_generate(
                prompt=prompt,
                output_schema=AnswerEvaluationOutput,
                system="You are a fair technical interview evaluator. Evaluate based on content, not style.",
                max_retries=2,
            )
        except Exception as exc:
            logger.warning("Answer evaluation failed", error=str(exc))
            eval_output = AnswerEvaluationOutput(
                correctness_score=5.0,
                depth_score=5.0,
                relevance_score=5.0,
                clarity_score=5.0,
                practical_understanding_score=5.0,
                evaluator_confidence=0.3,
                strengths=["Answer provided"],
                missing_concepts=[],
                incorrect_claims=[],
                recommended_next_action="continue",
            )

        # Persist evaluation
        evaluation = AnswerEvaluation(
            answer_id=answer.id,
            correctness_score=eval_output.correctness_score,
            depth_score=eval_output.depth_score,
            relevance_score=eval_output.relevance_score,
            clarity_score=eval_output.clarity_score,
            practical_understanding_score=eval_output.practical_understanding_score,
            evaluator_confidence=eval_output.evaluator_confidence,
            strengths=eval_output.strengths,
            weaknesses=eval_output.incorrect_claims,
            missing_concepts=eval_output.missing_concepts,
            recommended_next_action=eval_output.recommended_next_action,
        )
        self.db.add(evaluation)
        await self.db.flush()

        return eval_output
