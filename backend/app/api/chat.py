"""
api/chat.py — Chat message endpoints (Phase 0 stubs).

Full chat graph wired up in Phase 4.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import ChatMessage, Session as SessionModel
from backend.app.schemas import ChatMessageIn, ChatMessageOut

router = APIRouter(prefix="/sessions", tags=["chat"])


@router.get("/{session_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(
    session_id: int, db: AsyncSession = Depends(get_db)
) -> list[ChatMessageOut]:
    """Return the chat history for a session."""
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
    """Accept a user message. Phase 0: echoes back a placeholder response."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Persist user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=body.content)
    db.add(user_msg)

    # Stub assistant response (Phase 4 will call the chat graph)
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content="[Chat agent not yet implemented — Phase 0 stub. Upload an RFP to begin.]",
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)
    return ChatMessageOut.model_validate(assistant_msg)
