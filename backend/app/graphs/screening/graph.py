"""Candidate Screening LangGraph — Graph definition."""
from langgraph.graph import END, START, StateGraph

from app.graphs.screening.nodes import (
    calculate_deterministic_score,
    evaluate_education,
    evaluate_experience,
    evaluate_projects,
    evaluate_required_skills,
    generate_evidence_based_explanation,
    human_review_required_screening,
    load_candidate_profile,
    load_job_requirements,
    retrieve_relevant_resume_evidence,
    save_screening_result,
)
from app.graphs.screening.state import ScreeningState


def route_after_score(state: ScreeningState) -> str:
    if state.requires_human_review or state.confidence_score < 0.6:
        return "human_review_required"
    return "generate_evidence_based_explanation"


def build_screening_graph() -> StateGraph:
    """
    Candidate Screening LangGraph.
    
    Flow:
    START → load_job_requirements → load_candidate_profile
          → retrieve_relevant_resume_evidence
          → evaluate_required_skills (parallel in future)
          → evaluate_experience
          → evaluate_projects
          → evaluate_education
          → calculate_deterministic_score  ← deterministic, no LLM
          → [generate_explanation | human_review]
          → save_screening_result → END
    """
    workflow = StateGraph(ScreeningState)

    workflow.add_node("load_job_requirements", load_job_requirements)
    workflow.add_node("load_candidate_profile", load_candidate_profile)
    workflow.add_node("retrieve_relevant_resume_evidence", retrieve_relevant_resume_evidence)
    workflow.add_node("evaluate_required_skills", evaluate_required_skills)
    workflow.add_node("evaluate_experience", evaluate_experience)
    workflow.add_node("evaluate_projects", evaluate_projects)
    workflow.add_node("evaluate_education", evaluate_education)
    workflow.add_node("calculate_deterministic_score", calculate_deterministic_score)
    workflow.add_node("generate_evidence_based_explanation", generate_evidence_based_explanation)
    workflow.add_node("human_review_required", human_review_required_screening)
    workflow.add_node("save_screening_result", save_screening_result)

    workflow.add_edge(START, "load_job_requirements")
    workflow.add_edge("load_job_requirements", "load_candidate_profile")
    workflow.add_edge("load_candidate_profile", "retrieve_relevant_resume_evidence")
    workflow.add_edge("retrieve_relevant_resume_evidence", "evaluate_required_skills")
    workflow.add_edge("evaluate_required_skills", "evaluate_experience")
    workflow.add_edge("evaluate_experience", "evaluate_projects")
    workflow.add_edge("evaluate_projects", "evaluate_education")
    workflow.add_edge("evaluate_education", "calculate_deterministic_score")
    workflow.add_conditional_edges("calculate_deterministic_score", route_after_score)
    workflow.add_edge("generate_evidence_based_explanation", "save_screening_result")
    workflow.add_edge("human_review_required", "save_screening_result")
    workflow.add_edge("save_screening_result", END)

    return workflow


screening_graph = build_screening_graph().compile()
