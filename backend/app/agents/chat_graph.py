"""
backend/app/agents/chat_graph.py — LangGraph-powered conversational agent for Sales Engineers.

Orchestrates multi-turn dialogue, tool execution, citation provenance,
and human-in-the-loop approval guards.
"""

import json
import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from backend.app.agents.chat_tools import (
    CHAT_TOOLS_DEFINITIONS,
    execute_tool,
)
from backend.app.agents.prompts.chat_agent import CHAT_AGENT_SYSTEM_PROMPT
from backend.app.config import get_settings
from backend.app.db import AsyncSessionLocal
from backend.app.llm import _get_client
from backend.app.models import ChatMessage

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatState(TypedDict, total=False):
    session_id: int
    user_message: str
    history: list[dict[str, str]]
    tools_called: list[dict[str, Any]]
    response_text: str
    status: str


async def load_history_node(state: ChatState) -> dict[str, Any]:
    """Node 1: Load recent session chat history for conversational memory."""
    session_id = state["session_id"]
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(8)
        )
        recent_messages = list(reversed(res.scalars().all()))

    formatted_history = [
        {"role": m.role, "content": m.content}
        for m in recent_messages
        if m.role in ("user", "assistant")
    ]
    return {"history": formatted_history}


def _match_deterministic_intent(
    user_msg: str, session_id: int
) -> tuple[str | None, dict[str, Any]]:
    """Rule-based pattern matching fallback when LLM tool-calling is offline or in test mode."""
    msg = user_msg.strip()
    msg_lower = msg.lower()

    # Approve pattern: "approve 3.1 with confirm=True" or "approve 3.1"
    m_appr = re.search(r"approve\s+([0-9]+(?:\.[0-9]+)*)", msg_lower)
    if m_appr:
        q_num = m_appr.group(1)
        confirm = "confirm=true" in msg_lower or "confirmed" in msg_lower or "yes" in msg_lower
        return "approve_answer", {"question_number": q_num, "confirm": confirm}

    # Show pattern: "show answer 3.1" or "show 3.1" or "inspect 3.1"
    m_show = re.search(
        r"(?:show|view|inspect|get)(?:\s+answer)?\s+(?:for\s+)?([0-9]+(?:\.[0-9]+)*)", msg_lower
    )
    if m_show:
        return "show_answer", {"question_number": m_show.group(1)}

    # Rewrite pattern: "rewrite 3.1: <instruction>" or "rewrite question 3.1 to make it concise"
    m_rw = re.search(
        r"rewrite\s+(?:question\s+)?([0-9]+(?:\.[0-9]+)*)[\s:,-]+(.+)", msg, re.IGNORECASE
    )
    if m_rw:
        return "rewrite_answer", {
            "question_number": m_rw.group(1).strip(),
            "instruction": m_rw.group(2).strip(),
        }

    # Fact pattern: "add fact to 3.1: <fact>" or "apply fact 3.1: <fact>"
    m_fact = re.search(
        r"(?:add|apply)\s+fact\s+(?:to\s+)?([0-9]+(?:\.[0-9]+)*)[\s:,-]+(.+)", msg, re.IGNORECASE
    )
    if m_fact:
        return "apply_se_fact", {
            "question_number": m_fact.group(1).strip(),
            "fact": m_fact.group(2).strip(),
        }

    # List questions pattern: "list questions", "list pending", "list pricing"
    if "list" in msg_lower and (
        "question" in msg_lower
        or "pending" in msg_lower
        or "flagged" in msg_lower
        or "approved" in msg_lower
    ):
        status = None
        owner = None
        for s in ("pending", "answered", "clarification", "flagged_owner", "approved"):
            if s in msg_lower:
                status = s
                break
        for o in ("pricing", "legal", "delivery"):
            if o in msg_lower:
                owner = o.capitalize()
                break
        return "list_questions", {"status": status, "owner": owner}

    # Search KB pattern: "search kb: <query>" or "search for <query>"
    m_search = re.search(r"(?:search\s+kb|search\s+for|search)[\s:,-]+(.+)", msg, re.IGNORECASE)
    if m_search and len(m_search.group(1).strip()) > 2:
        return "search_kb", {"query": m_search.group(1).strip()}

    # Summary pattern: "summary", "status", "progress"
    if any(k in msg_lower for k in ("summary", "status", "progress", "overview")):
        return "get_rfp_summary", {}

    return None, {}


async def chat_agent_node(state: ChatState) -> dict[str, Any]:
    """Node 2: Invoke agent with OpenAI tool calling and multi-turn message loop."""
    session_id = state["session_id"]
    user_msg = state["user_message"]
    history = state.get("history", [])

    tools_called: list[dict[str, Any]] = []
    final_response = ""

    from backend.app.llm import has_valid_api_key

    if has_valid_api_key():
        try:
            client = _get_client()
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": CHAT_AGENT_SYSTEM_PROMPT},
                *history,
                {"role": "user", "content": user_msg},
            ]

            # Call LLM with tool declarations
            response = await client.chat.completions.create(
                model=settings.draft_model,
                messages=messages,
                tools=CHAT_TOOLS_DEFINITIONS,
                tool_choice="auto",
                temperature=0.2,
            )

            response_msg = response.choices[0].message

            # Check if tools were called
            if response_msg.tool_calls:
                # Add assistant message with tool calls to history
                messages.append(response_msg.model_dump())

                for tool_call in response_msg.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except Exception:
                        fn_args = {}

                    tool_result = await execute_tool(fn_name, fn_args, session_id=session_id)
                    tools_called.append({"tool": fn_name, "args": fn_args, "result": tool_result})

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result,
                        }
                    )

                # Follow-up completion to generate synthesized response
                followup = await client.chat.completions.create(
                    model=settings.draft_model,
                    messages=messages,
                    temperature=0.2,
                )
                final_response = followup.choices[0].message.content or ""
            else:
                final_response = response_msg.content or ""

        except Exception as exc:
            logger.warning(
                "LLM chat agent invocation failed (%s); falling back to intent matcher", exc
            )

    # If no response was generated (or fallback triggered), use deterministic matcher
    if not final_response:
        tool_name, tool_args = _match_deterministic_intent(user_msg, session_id)
        if tool_name:
            tool_result = await execute_tool(tool_name, tool_args, session_id=session_id)
            tools_called.append({"tool": tool_name, "args": tool_args, "result": tool_result})
            final_response = tool_result
        else:
            final_response = (
                "I am your Azentio RFP Assistant. You can ask me to:\n\n"
                '- **List questions**: *"List all pending questions"* or *"List pricing questions"*\n'
                '- **Inspect draft**: *"Show answer for 3.1"*\n'
                '- **Rewrite draft**: *"Rewrite 3.1: make it concise and emphasize AAOIFI compliance"*\n'
                '- **Inject SE fact**: *"Add fact to 3.1: Azentio has 4 live core banking deployments in the UAE"*\n'
                '- **Search knowledge base**: *"Search KB: Murabaha rebate calculation"*\n'
                '- **Approve answer**: *"Approve 3.1 with confirm=True"*\n'
                '- **Check progress**: *"Show RFP summary"*'
            )

    return {
        "tools_called": tools_called,
        "response_text": final_response,
    }


def build_chat_graph() -> Any:
    """Construct and compile the LangGraph chat workflow."""
    workflow = StateGraph(ChatState)

    workflow.add_node("load_history", load_history_node)
    workflow.add_node("chat_agent", chat_agent_node)

    workflow.add_edge(START, "load_history")
    workflow.add_edge("load_history", "chat_agent")
    workflow.add_edge("chat_agent", END)

    return workflow.compile()


# Compiled singleton chat graph
chat_graph = build_chat_graph()
