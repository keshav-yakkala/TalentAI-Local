"""
Adaptive Interview LangGraph — Graph definition.
Stateful, resumable interview with difficulty adaptation.
"""
from langgraph.graph import END, START, StateGraph

from app.graphs.interview.nodes import (
    create_interview_plan,
    evaluate_answer,
    generate_final_report,
    generate_next_question,
    load_candidate_context,
    transcribe_if_audio,
    update_interview_state,
)
from app.graphs.interview.state import AdaptiveInterviewState


def route_after_evaluation(state: AdaptiveInterviewState) -> str:
    """Decide whether to continue or finish the interview."""
    if state.interview_complete():
        return "generate_final_report"
    action = state.next_action or "continue"
    if action == "finish_interview":
        return "generate_final_report"
    return "update_interview_state"


def route_after_update(state: AdaptiveInterviewState) -> str:
    """After updating state, check if we continue."""
    if state.interview_complete():
        return "generate_final_report"
    return "generate_next_question"


def build_interview_graph() -> StateGraph:
    """
    Adaptive Interview LangGraph.
    
    Flow:
    START → load_context → create_plan → generate_question → [WAIT FOR ANSWER]
          → transcribe_if_audio → evaluate_answer
          → route: [finish → generate_final_report → END]
                  [continue → update_state → generate_question → loop]
    
    NOTE: The WAIT FOR ANSWER step uses interrupt() in LangGraph v2.
    The graph is paused at that point and resumed when the candidate submits.
    """
    workflow = StateGraph(AdaptiveInterviewState)

    workflow.add_node("load_candidate_context", load_candidate_context)
    workflow.add_node("create_interview_plan", create_interview_plan)
    workflow.add_node("generate_next_question", generate_next_question)
    workflow.add_node("transcribe_if_audio", transcribe_if_audio)
    workflow.add_node("evaluate_answer", evaluate_answer)
    workflow.add_node("update_interview_state", update_interview_state)
    workflow.add_node("generate_final_report", generate_final_report)

    workflow.add_edge(START, "load_candidate_context")
    workflow.add_edge("load_candidate_context", "create_interview_plan")
    workflow.add_edge("create_interview_plan", "generate_next_question")
    workflow.add_edge("generate_next_question", "transcribe_if_audio")
    workflow.add_edge("transcribe_if_audio", "evaluate_answer")
    workflow.add_conditional_edges("evaluate_answer", route_after_evaluation)
    workflow.add_conditional_edges("update_interview_state", route_after_update)
    workflow.add_edge("generate_final_report", END)

    return workflow


interview_graph = build_interview_graph().compile(
    # interrupt_before=["transcribe_if_audio"]  # Uncomment for human-in-loop pause
)
