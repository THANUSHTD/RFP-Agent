"""
agents/analyze_graph.py — LangGraph analysis pipeline for RFP processing.

Graph Flow:
    START
      │
      ▼
    extract_structure_node
      │
      ▼
    extract_format_rules_node
      │
      ▼
    draft_answers_node
      │
      ▼
    finalize_analysis_node
      │
      ▼
     END
"""
import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.db import AsyncSessionLocal
from backend.app.services.answer_drafter import draft_all_session_answers
from backend.app.services.rfp_analyzer import run_rfp_analysis

logger = logging.getLogger(__name__)


class AnalysisState(TypedDict, total=False):
    session_id: int
    summary: dict[str, Any]
    draft_summary: dict[str, Any]
    status: str
    error: str


async def parse_and_structure_node(state: AnalysisState) -> dict[str, Any]:
    """Node 1: Parse document, extract sections, discrete questions, and format rules."""
    session_id = state["session_id"]
    logger.info("LangGraph Analysis: Parsing structure for session %d", session_id)

    async with AsyncSessionLocal() as db:
        summary = await run_rfp_analysis(session_id, db)

    return {
        "summary": summary,
        "status": "structure_extracted",
    }


async def draft_answers_node(state: AnalysisState) -> dict[str, Any]:
    """Node 2: Retrieve context and draft verified answers for all questions."""
    session_id = state["session_id"]
    logger.info("LangGraph Analysis: Drafting answers for session %d", session_id)

    async with AsyncSessionLocal() as db:
        draft_summary = await draft_all_session_answers(session_id, db)

    return {
        "draft_summary": draft_summary,
        "status": "answers_drafted",
    }


async def finalize_analysis_node(state: AnalysisState) -> dict[str, Any]:
    """Node 3: Finalize and log analysis results."""
    session_id = state["session_id"]
    summary = state.get("summary", {})
    draft_summary = state.get("draft_summary", {})
    logger.info(
        "LangGraph Analysis complete for session %d: %d questions, %d answered, %d clarifications, %d flagged",
        session_id,
        summary.get("total_questions", 0),
        draft_summary.get("answered", 0),
        draft_summary.get("clarifications", 0),
        draft_summary.get("flagged", 0),
    )
    return {"status": "complete"}


def build_analysis_graph() -> Any:
    """Construct and compile the StateGraph for RFP analysis."""
    workflow = StateGraph(AnalysisState)

    workflow.add_node("parse_and_structure", parse_and_structure_node)
    workflow.add_node("draft_answers", draft_answers_node)
    workflow.add_node("finalize_analysis", finalize_analysis_node)

    workflow.add_edge(START, "parse_and_structure")
    workflow.add_edge("parse_and_structure", "draft_answers")
    workflow.add_edge("draft_answers", "finalize_analysis")
    workflow.add_edge("finalize_analysis", END)

    return workflow.compile()


# Compiled analysis graph singleton
analysis_graph = build_analysis_graph()
