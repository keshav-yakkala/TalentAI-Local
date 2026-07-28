"""
Adaptive Interview LangGraph — Nodes
Stateful interview that adapts difficulty in real-time.

Key upgrade from original ui.py:
- Binary yes/no evaluation → multi-dimensional scores (0-10 per category)
- Fixed 5 questions → adaptive up to max_questions based on performance
- No context → full resume + JD context for each question
- Blocking UI transcription → async Whisper service
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.graphs.interview.state import (
    AdaptiveInterviewState,
    InterviewPlan,
    QuestionRecord,
)

logger = get_logger(__name__)


# ── Node: load_candidate_context ──────────────────────────────────────────────

async def load_candidate_context(state: AdaptiveInterviewState) -> dict[str, Any]:
    """Load candidate's resume profile and interview context from DB."""
    logger.info("Loading interview context", interview_id=state.interview_id)
    # TODO Phase 9 full: Query DB for candidate profile
    return {"current_status": "planning"}


# ── Node: create_interview_plan ───────────────────────────────────────────────

async def create_interview_plan(state: AdaptiveInterviewState) -> dict[str, Any]:
    """
    Create a structured interview plan based on the candidate's resume and JD.
    Identifies gaps, strong areas, and key topics to probe.
    """
    from app.ai.llms.factory import get_llm_provider
    from pydantic import BaseModel

    logger.info("Creating interview plan", interview_id=state.interview_id)

    llm = get_llm_provider()

    resume_ctx = state.resume_profile_json or "No resume profile available"
    jd_ctx = state.jd_analysis_json or "No JD analysis available"

    prompt = f"""Create an interview plan for a candidate.

Resume Profile: {resume_ctx[:2000]}
Job Requirements: {jd_ctx[:1000]}

Identify:
1. Key required skills to probe (from JD requirements)
2. Resume weak spots (gaps or unclear claims to investigate)
3. Topics for the interview (in priority order)
4. Recommended number of questions (6-10)

Respond with InterviewPlan JSON."""

    try:
        plan = await llm.structured_generate(prompt, InterviewPlan, max_retries=2)
        topics_remaining = list(plan.topics_to_cover)
        return {
            "interview_plan": plan,
            "topics_remaining": topics_remaining,
            "current_status": "questioning",
        }
    except Exception as exc:
        logger.warning("Interview planning failed, using defaults", error=str(exc))
        default_plan = InterviewPlan(
            topics_to_cover=["Technical Skills", "Experience", "Projects"],
            key_required_skills=[],
            estimated_question_count=8,
        )
        return {
            "interview_plan": default_plan,
            "topics_remaining": default_plan.topics_to_cover,
            "current_status": "questioning",
        }


# ── Node: generate_next_question ──────────────────────────────────────────────

async def generate_next_question(state: AdaptiveInterviewState) -> dict[str, Any]:
    """
    Generate the next interview question adapted to:
    - Current difficulty level (adapts based on recent answer quality)
    - Topics remaining to cover
    - Conversation history (no repeat questions)
    - Resume-specific context (based on what we know about the candidate)
    """
    from app.ai.llms.factory import get_llm_provider
    from app.ai.structured_outputs.screening import InterviewQuestionOutput

    logger.info(
        "Generating next question",
        interview_id=state.interview_id,
        question_num=state.current_question_number + 1,
        difficulty=state.current_difficulty,
        topic=state.topics_remaining[0] if state.topics_remaining else "general",
    )

    llm = get_llm_provider()

    # Build conversation history summary
    history = ""
    if state.questions:
        recent = state.questions[-3:]  # Last 3 Q&A pairs for context
        history = "\n".join([
            f"Q{r.sequence_number}: {r.question}\nA: {r.answer_text or '(no answer yet)'}"
            for r in recent
        ])

    topic = state.topics_remaining[0] if state.topics_remaining else "general technical"
    resume_ctx = state.resume_profile_json[:1500] if state.resume_profile_json else ""

    prompt = f"""Generate interview question #{state.current_question_number + 1}.

Topic to cover: {topic}
Difficulty: {state.current_difficulty}
Candidate Resume: {resume_ctx}
Job Requirements: {state.jd_analysis_json[:500] if state.jd_analysis_json else ""}

Previous questions asked:
{history or "(first question)"}

Generate ONE specific, targeted question. It should:
- Be at {state.current_difficulty} difficulty
- Test the candidate's actual knowledge (not just definitions)
- Reference their specific projects/experience when possible
- Not repeat any previous question

Respond with InterviewQuestionOutput JSON."""

    try:
        question = await llm.structured_generate(prompt, InterviewQuestionOutput, max_retries=2)
        return {
            "current_question": question,
            "waiting_for_answer": True,
            "current_question_number": state.current_question_number + 1,
        }
    except Exception as exc:
        logger.error("Question generation failed", error=str(exc))
        return {"errors": [*state.errors, f"Question generation failed: {exc}"]}


# ── Node: transcribe_if_audio ─────────────────────────────────────────────────

async def transcribe_if_audio(state: AdaptiveInterviewState) -> dict[str, Any]:
    """
    Transcribe audio answer using Whisper if audio was provided.
    Migrated from ui.py where Whisper ran blocking in the Streamlit UI thread.
    Now runs as an async background service.
    """
    if not state.pending_audio_path:
        return {}  # Text answer, no transcription needed

    logger.info("Transcribing audio answer", interview_id=state.interview_id)

    try:
        import asyncio
        import whisper

        def _transcribe(audio_path: str) -> str:
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return result["text"]

        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(None, _transcribe, state.pending_audio_path)

        # Update the latest question record with transcription
        if state.questions:
            latest = state.questions[-1]
            latest.transcription = transcription
            latest.answer_text = transcription

        logger.info("Transcription complete", length=len(transcription))
        return {"pending_audio_path": None}

    except ImportError:
        logger.warning("Whisper not installed, skipping transcription")
        return {"pending_audio_path": None}
    except Exception as exc:
        logger.error("Transcription failed", error=str(exc))
        return {
            "errors": [*state.errors, f"Transcription failed: {exc}"],
            "pending_audio_path": None,
        }


# ── Node: evaluate_answer ─────────────────────────────────────────────────────

async def evaluate_answer(state: AdaptiveInterviewState) -> dict[str, Any]:
    """
    Multi-dimensional answer evaluation.
    
    Original ui.py returned binary "Yes"/"No".
    This returns 5 dimensions (0-10 each) with evidence:
    - Correctness, Depth, Relevance, Clarity, Practical Understanding
    """
    from app.ai.llms.factory import get_llm_provider
    from app.ai.structured_outputs.screening import AnswerEvaluationOutput

    if not state.questions:
        return {}

    latest = state.questions[-1]
    answer = latest.answer_text or latest.transcription or ""

    if not answer.strip():
        logger.warning("Empty answer received", interview_id=state.interview_id)
        return {}

    logger.info("Evaluating answer", interview_id=state.interview_id, question_num=latest.sequence_number)

    llm = get_llm_provider()

    prompt = f"""Evaluate this interview answer.

Question: {latest.question}
Question Type: {latest.question_type}
Expected Topic: {latest.topic}

Candidate's Answer:
{answer}

Job Context: {state.jd_analysis_json[:300] if state.jd_analysis_json else ""}

Score each dimension 0.0-10.0:
- correctness_score: Is the answer factually correct?
- depth_score: Does the candidate show deep understanding or surface knowledge?
- relevance_score: Does the answer address the question asked?
- clarity_score: Is the answer clear and well-structured?
- practical_understanding_score: Does the candidate show real-world application knowledge?

Also provide:
- evaluator_confidence (0.0-1.0): How confident are you in this evaluation?
- strengths: What did they do well?
- missing_concepts: What key concepts were missed?
- incorrect_claims: Any factually wrong statements?
- recommended_next_action: One of [deeper_question, clarification, increase_difficulty, decrease_difficulty, change_topic, continue, finish_interview]

Respond with AnswerEvaluationOutput JSON."""

    try:
        evaluation = await llm.structured_generate(prompt, AnswerEvaluationOutput, max_retries=2)
        latest.evaluation = evaluation

        # Update cumulative scores
        new_scores = {
            "correctness": [*state.cumulative_scores["correctness"], evaluation.correctness_score],
            "depth": [*state.cumulative_scores["depth"], evaluation.depth_score],
            "relevance": [*state.cumulative_scores["relevance"], evaluation.relevance_score],
            "clarity": [*state.cumulative_scores["clarity"], evaluation.clarity_score],
            "practical": [*state.cumulative_scores["practical"], evaluation.practical_understanding_score],
        }

        return {
            "questions": state.questions,
            "cumulative_scores": new_scores,
            "next_action": evaluation.recommended_next_action,
        }
    except Exception as exc:
        logger.error("Answer evaluation failed", error=str(exc))
        return {"errors": [*state.errors, str(exc)], "next_action": "continue"}


# ── Node: update_interview_state ──────────────────────────────────────────────

def update_interview_state(state: AdaptiveInterviewState) -> dict[str, Any]:
    """
    Update difficulty and tracking based on the latest evaluation.
    This is pure deterministic logic — no LLM calls.
    """
    if not state.questions or not state.questions[-1].evaluation:
        return {}

    latest_eval = state.questions[-1].evaluation
    avg_score = (
        latest_eval.correctness_score + latest_eval.depth_score +
        latest_eval.practical_understanding_score
    ) / 3

    new_consecutive_strong = state.consecutive_strong
    new_consecutive_weak = state.consecutive_weak
    new_difficulty = state.current_difficulty

    if avg_score >= 7.5:
        new_consecutive_strong += 1
        new_consecutive_weak = 0
    elif avg_score < 4.0:
        new_consecutive_weak += 1
        new_consecutive_strong = 0
    else:
        new_consecutive_strong = max(0, new_consecutive_strong - 1)
        new_consecutive_weak = max(0, new_consecutive_weak - 1)

    # Adapt difficulty
    if new_consecutive_strong >= 2 and new_difficulty != "hard":
        new_difficulty = "medium" if new_difficulty == "easy" else "hard"
        logger.info("Difficulty increased", interview_id=state.interview_id, new=new_difficulty)
        new_consecutive_strong = 0
    elif new_consecutive_weak >= 2 and new_difficulty != "easy":
        new_difficulty = "medium" if new_difficulty == "hard" else "easy"
        logger.info("Difficulty decreased", interview_id=state.interview_id, new=new_difficulty)
        new_consecutive_weak = 0

    # Update topics covered
    topics_remaining = state.topics_remaining[:]
    if state.current_question and state.current_question.topic in topics_remaining:
        topics_remaining.remove(state.current_question.topic)
        topics_covered = [*state.topics_covered, state.current_question.topic]
    else:
        topics_covered = state.topics_covered

    return {
        "consecutive_strong": new_consecutive_strong,
        "consecutive_weak": new_consecutive_weak,
        "current_difficulty": new_difficulty,
        "topics_remaining": topics_remaining,
        "topics_covered": topics_covered,
        "waiting_for_answer": False,
    }


# ── Node: generate_final_report ───────────────────────────────────────────────

async def generate_final_report(state: AdaptiveInterviewState) -> dict[str, Any]:
    """Generate the final interview report from all accumulated scores."""
    from app.ai.llms.factory import get_llm_provider

    logger.info("Generating final report", interview_id=state.interview_id)

    # Calculate final scores deterministically
    def avg(lst: list[float]) -> float:
        return (sum(lst) / len(lst) * 10) if lst else 0.0  # Scale to 0-100

    technical_score = avg(state.cumulative_scores.get("correctness", []) +
                         state.cumulative_scores.get("depth", []))
    communication_score = avg(state.cumulative_scores.get("clarity", []))
    problem_solving_score = avg(state.cumulative_scores.get("practical", []))

    # LLM generates narrative summary from structured data
    llm = get_llm_provider()
    qa_summary = "\n".join([
        f"Q{r.sequence_number} ({r.topic}): Score {r.evaluation.correctness_score:.1f}/10"
        for r in state.questions if r.evaluation
    ])

    prompt = f"""Write a final interview report for a recruiter (3-4 paragraphs).

Candidate Performance Summary:
- Technical Score: {technical_score:.0f}/100
- Communication Score: {communication_score:.0f}/100
- Problem Solving Score: {problem_solving_score:.0f}/100

Question-by-Question Summary:
{qa_summary}

Topics Covered: {', '.join(state.topics_covered)}

Write a professional, evidence-based report. Highlight strengths and areas for improvement.
End with a hiring recommendation: Strong Hire / Hire / Maybe / No Hire."""

    try:
        report_text = await llm.generate(prompt)
    except Exception:
        report_text = f"Interview completed with {len(state.questions)} questions. Technical: {technical_score:.0f}/100."

    return {
        "technical_score": round(technical_score, 2),
        "communication_score": round(communication_score, 2),
        "problem_solving_score": round(problem_solving_score, 2),
        "final_report_generated": True,
        "current_status": "completed",
    }
