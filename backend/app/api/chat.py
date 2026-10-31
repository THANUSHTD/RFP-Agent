"""
api/chat.py — Sales Engineer chat workspace endpoints.

Full conversational agent powered by LangGraph, with interactive tool calling:
- Listing questions by status / owner / category
- Inspecting draft answers & citations
- Rewriting drafts according to SE instructions
- Injecting SE field knowledge / facts with 'se_input' citations
- Searching the Knowledge Base
- Approving answers with explicit SE confirmation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.chat_graph import chat_graph
from backend.app.db import get_db
from backend.app.models import ChatMessage
from backend.app.models import Session as SessionModel
from backend.app.schemas import ChatMessageIn, ChatMessageOut

router = APIRouter(prefix="/sessions", tags=["chat"])


@router.get("/{session_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> list[ChatMessageOut]:
    """Return the chronological chat history for a session."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return [ChatMessageOut.model_validate(m) for m in result.scalars()]


@router.post("/{session_id}/chat", response_model=ChatMessageOut)
async def post_message(
    session_id: int, body: ChatMessageIn, db: AsyncSession = Depends(get_db)
) -> ChatMessageOut:
    """Accept a user message, invoke the LangGraph chat agent, and return assistant response."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Persist user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)
    await db.commit()

    # 2. Invoke LangGraph chat agent
    result = await chat_graph.ainvoke(
        {
            "session_id": session_id,
            "user_message": body.content,
        }
    )
    response_text = result.get("response_text", "")

    # 3. Persist assistant message on request DB session
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response_text,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatMessageOut.model_validate(assistant_msg)
