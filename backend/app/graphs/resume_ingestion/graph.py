"""
Resume Ingestion LangGraph — Graph definition.
Implements the full state machine with conditional routing and retry logic.
"""
from langgraph.graph import END, START, StateGraph

from app.graphs.resume_ingestion.nodes import (
    clean_text,
    create_semantic_chunks,
    detect_sections,
    extract_structured_resume,
    extract_text,
    fallback_parser,
    generate_embeddings,
    human_review_required,
    mark_failed,
    retry_extraction,
    store_structured_data,
    store_vectors,
    validate_extraction,
    validate_file,
)
from app.graphs.resume_ingestion.state import ResumeIngestionState


# ── Conditional routing functions ─────────────────────────────────────────────


def route_after_validate_file(state: ResumeIngestionState) -> str:
    if state.current_status == "failed":
        return "mark_failed"
    return "extract_text"


def route_after_extract_text(state: ResumeIngestionState) -> str:
    if state.current_status == "fallback_needed":
        return "fallback_parser"
    if state.current_status in ("failed",):
        return "mark_failed"
    return "clean_text"


def route_after_fallback(state: ResumeIngestionState) -> str:
    if state.current_status == "failed":
        return "mark_failed"
    if state.requires_human_review:
        return "human_review_required"
    return "clean_text"


def route_after_validate_extraction(state: ResumeIngestionState) -> str:
    """
    Core routing logic after extraction quality check.
    Implements the retry + human-review pattern.
    IMPORTANT: retry_count prevents infinite loops.
    """
    confidence = state.extraction_confidence

    if confidence >= 0.7:
        return "create_semantic_chunks"

    if confidence < 0.4:
        # Very low confidence — skip retries, go straight to human review
        return "human_review_required"

    # Medium confidence — retry if budget allows
    if state.can_retry():
        return "retry_extraction"

    return "human_review_required"


# ── Build graph ───────────────────────────────────────────────────────────────


def build_resume_ingestion_graph() -> StateGraph:
    """
    Constructs the Resume Ingestion LangGraph.

    Flow:
    START → validate_file → extract_text → clean_text → detect_sections
          → extract_structured_resume → validate_extraction
          → [create_semantic_chunks | retry_extraction | human_review_required]
          → generate_embeddings → store_vectors → store_structured_data → END
    """
    workflow = StateGraph(ResumeIngestionState)

    # Add nodes
    workflow.add_node("validate_file", validate_file)
    workflow.add_node("extract_text", extract_text)
    workflow.add_node("fallback_parser", fallback_parser)
    workflow.add_node("clean_text", clean_text)
    workflow.add_node("detect_sections", detect_sections)
    workflow.add_node("extract_structured_resume", extract_structured_resume)
    workflow.add_node("validate_extraction", validate_extraction)
    workflow.add_node("retry_extraction", retry_extraction)
    workflow.add_node("create_semantic_chunks", create_semantic_chunks)
    workflow.add_node("generate_embeddings", generate_embeddings)
    workflow.add_node("store_vectors", store_vectors)
    workflow.add_node("store_structured_data", store_structured_data)
    workflow.add_node("human_review_required", human_review_required)
    workflow.add_node("mark_failed", mark_failed)

    # Edges
    workflow.add_edge(START, "validate_file")
    workflow.add_conditional_edges("validate_file", route_after_validate_file)
    workflow.add_conditional_edges("extract_text", route_after_extract_text)
    workflow.add_conditional_edges("fallback_parser", route_after_fallback)
    workflow.add_edge("clean_text", "detect_sections")
    workflow.add_edge("detect_sections", "extract_structured_resume")
    workflow.add_edge("extract_structured_resume", "validate_extraction")
    workflow.add_conditional_edges("validate_extraction", route_after_validate_extraction)
    workflow.add_edge("retry_extraction", "extract_structured_resume")  # Loop back — retry_count limits this
    workflow.add_edge("create_semantic_chunks", "generate_embeddings")
    workflow.add_edge("generate_embeddings", "store_vectors")
    workflow.add_edge("store_vectors", "store_structured_data")
    workflow.add_edge("store_structured_data", END)
    workflow.add_edge("human_review_required", END)
    workflow.add_edge("mark_failed", END)

    return workflow


# Compile the graph for use
resume_ingestion_graph = build_resume_ingestion_graph().compile()
