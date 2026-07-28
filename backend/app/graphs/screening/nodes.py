"""
Candidate Screening LangGraph — Nodes
Evidence-based, weighted candidate scoring.

The original agents.py used:
    total_skill_score = sum(scores) / (10 * len(skills)) * 100
    flat average, no weighting, no evidence, no categories

This implementation:
- 7 weighted scoring categories
- LLM provides EVIDENCE for each match (exact resume quotes)
- DETERMINISTIC final score calculated from weighted category scores
- LLM never directly sets the final score — it provides evidence only
- Human review triggered at confidence < 0.6
"""
from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.graphs.screening.state import ScreeningState

logger = get_logger(__name__)


# ── Node: load_job_requirements ───────────────────────────────────────────────

async def load_job_requirements(state: ScreeningState) -> dict[str, Any]:
    """Load JD analysis from database."""
    logger.info("Loading job requirements", job_id=state.job_id)
    # TODO: Query DB for JobRequirements and reconstruct JDAnalysis
    # For now returns placeholder
    return {"current_status": "loading_candidate"}


# ── Node: load_candidate_profile ─────────────────────────────────────────────

async def load_candidate_profile(state: ScreeningState) -> dict[str, Any]:
    """Load candidate's structured profile from DB."""
    logger.info("Loading candidate profile", candidate_id=state.candidate_id)
    return {"current_status": "retrieving_evidence"}


# ── Node: retrieve_relevant_resume_evidence ───────────────────────────────────

async def retrieve_relevant_resume_evidence(state: ScreeningState) -> dict[str, Any]:
    """
    Use pgvector to retrieve the most relevant resume chunks for each JD requirement.
    This is the RAG step that grounds the evaluation in actual resume text.
    """
    from app.ai.embeddings.local_provider import get_embedding_provider
    from app.rag.vector_store.pgvector_store import PGVectorStore
    from sqlalchemy.ext.asyncio import AsyncSession
    import uuid

    logger.info("Retrieving resume evidence", candidate_id=state.candidate_id)

    # Build a query from the job requirements
    if not state.jd_analysis:
        return {"retrieved_chunks": [], "current_status": "evaluating_skills"}

    # Embed the key requirements for retrieval
    all_requirements = " ".join([
        s.name for s in (state.jd_analysis.required_skills + state.jd_analysis.preferred_skills)
    ])

    # NOTE: DB session would be injected in production — simplified here
    logger.info("Evidence retrieval complete (stub)", candidate_id=state.candidate_id)
    return {"current_status": "evaluating_skills"}


# ── Node: evaluate_required_skills ────────────────────────────────────────────

async def evaluate_required_skills(state: ScreeningState) -> dict[str, Any]:
    """
    Evaluate candidate's required skills against JD requirements.
    LLM provides evidence; scores are bounded by Pydantic schema.
    """
    from app.ai.llms.factory import get_llm_provider
    from app.ai.structured_outputs.screening import SkillMatchEvidence
    from app.ai.prompts.jd_analysis import build_skill_matching_prompt
    import json

    logger.info("Evaluating required skills", candidate_id=state.candidate_id)

    if not state.jd_analysis or not state.resume_profile_json:
        return {"required_skills_score": 0.0}

    llm = get_llm_provider()

    # Build context from retrieved chunks
    chunks_context = "\n\n".join(
        c.get("content", "") for c in state.retrieved_chunks[:5]
    )

    prompt = f"""Evaluate if the candidate has these required skills: {json.dumps([s.name for s in state.jd_analysis.required_skills])}

Resume Profile: {state.resume_profile_json[:3000]}

Resume Evidence: {chunks_context[:2000]}

For each skill, respond with JSON:
{{
  "skill_matches": [
    {{"skill_name": "Python", "found": true, "evidence": "exact quote", "confidence": 0.9, "proficiency_level": "advanced"}},
    ...
  ]
}}

Only mark found=true if there is explicit evidence in the resume."""

    try:
        from pydantic import BaseModel

        class SkillMatchList(BaseModel):
            skill_matches: list[SkillMatchEvidence]

        result = await llm.structured_generate(prompt, SkillMatchList)
        matches = result.skill_matches

        # Deterministic scoring — LLM provides evidence, code calculates score
        if not matches:
            return {"required_skills_score": 0.0}

        found_count = sum(1 for m in matches if m.found)
        total = len(matches)
        score = (found_count / total) * 100 if total > 0 else 0.0

        # Apply confidence weighting
        avg_confidence = sum(m.confidence for m in matches) / len(matches) if matches else 0.0
        weighted_score = score * avg_confidence

        missing = [m.skill_name for m in matches if not m.found]

        return {
            "required_skills_score": round(weighted_score, 2),
            "missing_required_skills": missing,
            "evidence_json": {
                **(state.evidence_json or {}),
                "required_skills": [m.model_dump() for m in matches],
            },
        }
    except Exception as exc:
        logger.warning("Required skills evaluation failed", error=str(exc))
        return {"required_skills_score": 0.0, "errors": [*state.errors, str(exc)]}


# ── Node: evaluate_experience ─────────────────────────────────────────────────

async def evaluate_experience(state: ScreeningState) -> dict[str, Any]:
    """Evaluate total years of experience against JD requirements."""
    from app.ai.llms.factory import get_llm_provider
    from app.ai.structured_outputs.screening import CategoryScore

    logger.info("Evaluating experience", candidate_id=state.candidate_id)

    if not state.jd_analysis or not state.resume_profile_json:
        return {"experience_score": 0.0}

    min_years = state.jd_analysis.min_years_experience or 0.0
    llm = get_llm_provider()

    prompt = f"""Evaluate candidate's work experience against the job requirement of {min_years} minimum years.

Resume Profile: {state.resume_profile_json[:2000]}

Respond with JSON:
{{
  "score": 75.0,
  "evidence": ["3 years at Company A as Software Engineer", "2 years at Company B"],
  "explanation": "Candidate has 5 years total experience, meets {min_years} year requirement",
  "confidence": 0.85
}}

Score 0-100:
- 100: Significantly exceeds requirement with relevant experience
- 75: Meets or slightly exceeds requirement  
- 50: Slightly below requirement
- 25: Significantly below requirement
- 0: No work experience found"""

    try:
        result = await llm.structured_generate(prompt, CategoryScore)
        return {
            "experience_score": round(result.score, 2),
            "evidence_json": {
                **(state.evidence_json or {}),
                "experience": result.model_dump(),
            },
        }
    except Exception as exc:
        logger.warning("Experience evaluation failed", error=str(exc))
        return {"experience_score": 0.0}


# ── Node: evaluate_projects ───────────────────────────────────────────────────

async def evaluate_projects(state: ScreeningState) -> dict[str, Any]:
    """Evaluate relevance and quality of candidate's projects."""
    from app.ai.llms.factory import get_llm_provider
    from app.ai.structured_outputs.screening import CategoryScore

    logger.info("Evaluating projects", candidate_id=state.candidate_id)

    if not state.resume_profile_json:
        return {"project_score": 0.0}

    llm = get_llm_provider()
    chunks_context = "\n\n".join(c.get("content", "") for c in state.retrieved_chunks if c.get("section_type") == "project")

    prompt = f"""Evaluate the candidate's projects for relevance to the job.

Job Required Skills: {[s.name for s in state.jd_analysis.required_skills] if state.jd_analysis else []}

Project Information:
{chunks_context[:3000] or state.resume_profile_json[:1500]}

Score 0-100 based on:
- Relevance of technologies used to job requirements
- Complexity and impact of projects
- Evidence of practical application of required skills

Respond with JSON matching CategoryScore schema."""

    try:
        result = await llm.structured_generate(prompt, CategoryScore)
        return {"project_score": round(result.score, 2)}
    except Exception as exc:
        return {"project_score": 0.0, "errors": [*state.errors, str(exc)]}


# ── Node: evaluate_education ──────────────────────────────────────────────────

async def evaluate_education(state: ScreeningState) -> dict[str, Any]:
    """Evaluate education against job requirements."""
    from app.ai.llms.factory import get_llm_provider
    from app.ai.structured_outputs.screening import CategoryScore

    if not state.resume_profile_json:
        return {"education_score": 50.0}  # Neutral if no data

    llm = get_llm_provider()
    edu_req = state.jd_analysis.education_requirement if state.jd_analysis else "Not specified"

    prompt = f"""Evaluate the candidate's education.

Required Education: {edu_req}
Resume Profile: {state.resume_profile_json[:1500]}

Score 0-100. Respond with CategoryScore JSON."""

    try:
        result = await llm.structured_generate(prompt, CategoryScore)
        return {"education_score": round(result.score, 2)}
    except Exception:
        return {"education_score": 50.0}


# ── Node: calculate_deterministic_score ───────────────────────────────────────

def calculate_deterministic_score(state: ScreeningState) -> dict[str, Any]:
    """
    Calculate the final weighted score DETERMINISTICALLY from category scores.
    
    The LLM provides evidence and category scores.
    This node applies the configured weights to calculate the final score.
    The LLM NEVER directly sets the final score — this prevents score manipulation.
    
    Weights are configurable via environment variables (must sum to 1.0).
    """
    weights = {
        "required_skills": settings.SCREENING_WEIGHT_REQUIRED_SKILLS,
        "experience": settings.SCREENING_WEIGHT_EXPERIENCE,
        "projects": settings.SCREENING_WEIGHT_PROJECTS,
        "preferred_skills": settings.SCREENING_WEIGHT_PREFERRED_SKILLS,
        "education": settings.SCREENING_WEIGHT_EDUCATION,
        "domain": settings.SCREENING_WEIGHT_DOMAIN,
        "semantic_match": settings.SCREENING_WEIGHT_SEMANTIC_MATCH,
    }

    scores = {
        "required_skills": state.required_skills_score,
        "experience": state.experience_score,
        "projects": state.project_score,
        "preferred_skills": state.preferred_skills_score,
        "education": state.education_score,
        "domain": state.domain_score,
        "semantic_match": state.semantic_match_score,
    }

    overall = sum(scores[k] * weights[k] for k in weights)

    # Confidence: penalize if many categories had no data
    non_zero_categories = sum(1 for v in scores.values() if v > 0)
    confidence = min(1.0, non_zero_categories / len(scores))

    # Recommendation thresholds
    if overall >= 75:
        recommendation = "strong_match"
    elif overall >= 55:
        recommendation = "potential_match"
    elif confidence < 0.6:
        recommendation = "needs_human_review"
    else:
        recommendation = "weak_match"

    requires_review = confidence < 0.6 or recommendation == "needs_human_review"

    logger.info(
        "Deterministic score calculated",
        candidate_id=state.candidate_id,
        overall=overall,
        confidence=confidence,
        recommendation=recommendation,
        category_scores=scores,
    )

    return {
        "overall_score": round(overall, 2),
        "confidence_score": round(confidence, 2),
        "recommendation": recommendation,
        "requires_human_review": requires_review,
        "current_status": "generating_explanation",
    }


# ── Node: generate_evidence_based_explanation ─────────────────────────────────

async def generate_evidence_based_explanation(state: ScreeningState) -> dict[str, Any]:
    """Generate a human-readable explanation of the screening result."""
    from app.ai.llms.factory import get_llm_provider

    llm = get_llm_provider()

    missing = ", ".join(state.missing_required_skills) if state.missing_required_skills else "None"
    prompt = f"""Write a concise recruiter summary (3-5 sentences) for this candidate screening result.

Overall Score: {state.overall_score:.0f}/100
Recommendation: {state.recommendation}
Required Skills Score: {state.required_skills_score:.0f}/100
Experience Score: {state.experience_score:.0f}/100
Projects Score: {state.project_score:.0f}/100
Missing Required Skills: {missing}

Write a professional, factual summary. Do not invent information.
Focus on what was found and what is missing."""

    try:
        explanation = await llm.generate(prompt)
        return {"explanation": explanation, "current_status": "saving_result"}
    except Exception as exc:
        return {
            "explanation": f"Screening completed. Score: {state.overall_score:.0f}/100. Recommendation: {state.recommendation}.",
            "errors": [*state.errors, str(exc)],
        }


# ── Node: save_screening_result ───────────────────────────────────────────────

async def save_screening_result(state: ScreeningState) -> dict[str, Any]:
    """Persist screening result to database."""
    logger.info(
        "Saving screening result",
        application_id=state.application_id,
        overall_score=state.overall_score,
        recommendation=state.recommendation,
    )
    # TODO: DB persistence in Phase 8 full implementation
    return {"current_status": "completed"}


# ── Node: human_review_required ───────────────────────────────────────────────

def human_review_required_screening(state: ScreeningState) -> dict[str, Any]:
    """Route to human review when confidence is too low."""
    logger.warning(
        "Screening routed to human review",
        application_id=state.application_id,
        confidence=state.confidence_score,
        overall_score=state.overall_score,
    )
    return {
        "current_status": "human_review_required",
        "requires_human_review": True,
        "human_review_reason": f"Confidence {state.confidence_score:.2f} below threshold.",
    }
