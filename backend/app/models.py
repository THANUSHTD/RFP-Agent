"""
models.py — SQLAlchemy ORM models (data model / schema definition).

All tables documented in the brief are defined here.
We use SQLAlchemy 2.0-style mapped_column / Mapped for full typing support.
"""
import json
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ── Enums ────────────────────────────────────────────────────────────────────

class QuestionKind(str, PyEnum):
    narrative = "narrative"
    table_row = "table_row"
    compliance_item = "compliance_item"


class QuestionCategory(str, PyEnum):
    technical = "technical"
    functional = "functional"
    shariah = "shariah"
    commercial = "commercial"
    legal = "legal"
    sla = "sla"
    other = "other"


class QuestionStatus(str, PyEnum):
    pending = "pending"
    answered = "answered"
    low_confidence = "low_confidence"
    clarification = "clarification"
    flagged_owner = "flagged_owner"
    approved = "approved"


class OwnerDept(str, PyEnum):
    pricing = "Pricing"
    legal = "Legal"
    delivery = "Delivery"


class AnswerStatus(str, PyEnum):
    draft = "draft"
    approved = "approved"


class SourceType(str, PyEnum):
    product_doc = "product_doc"
    sow = "sow"
    past_response = "past_response"


class ClarificationStatus(str, PyEnum):
    open = "open"
    resolved = "resolved"


# ── Tables ───────────────────────────────────────────────────────────────────

class Session(Base):
    """One RFP engagement / workspace."""
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    rfp_documents: Mapped[list["RFPDocument"]] = relationship(back_populates="session")
    questions: Mapped[list["Question"]] = relationship(back_populates="session")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session")
    clarifications: Mapped[list["Clarification"]] = relationship(back_populates="session")


class RFPDocument(Base):
    """Uploaded RFP file attached to a session."""
    __tablename__ = "rfp_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | docx
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["Session"] = relationship(back_populates="rfp_documents")
    sections: Mapped[list["Section"]] = relationship(back_populates="rfp_document")


class Section(Base):
    """A top-level section extracted from an RFP."""
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rfp_document_id: Mapped[int] = mapped_column(ForeignKey("rfp_documents.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    page_start: Mapped[int | None] = mapped_column(Integer)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    rfp_document: Mapped["RFPDocument"] = relationship(back_populates="sections")
    questions: Mapped[list["Question"]] = relationship(back_populates="section")


class Question(Base):
    """An individual requirement / question extracted from the RFP."""
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"))
    number: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "3.2.1"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    kind: Mapped[str] = mapped_column(String(30), default=QuestionKind.narrative)
    category: Mapped[str] = mapped_column(String(30), default=QuestionCategory.other)
    status: Mapped[str] = mapped_column(String(30), default=QuestionStatus.pending)
    owner: Mapped[str | None] = mapped_column(String(30))  # Pricing | Legal | Delivery
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="questions")
    section: Mapped["Section | None"] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question")


class Answer(Base):
    """Versioned draft answer for a question.

    Multiple versions can exist per question; the latest is the active draft.
    """
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # JSON list of citation objects: {chunk_id, document, source_type, snippet}
    # or {type: "se_input", fact: "..."}
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    # JSON list of stale-warning strings
    stale_warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default=AnswerStatus.draft)
    edited_by_se: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    question: Mapped["Question"] = relationship(back_populates="answers")

    @property
    def citations(self) -> list[dict[str, Any]]:
        return json.loads(self.citations_json)

    @property
    def stale_warnings(self) -> list[str]:
        return json.loads(self.stale_warnings_json)


class Clarification(Base):
    """A question the agent cannot answer; needs human input."""
    __tablename__ = "clarifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON list of question IDs linked to this clarification
    linked_question_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default=ClarificationStatus.open)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="clarifications")

    @property
    def linked_question_ids(self) -> list[int]:
        return json.loads(self.linked_question_ids_json)


class ChatMessage(Base):
    """A message in the SE-agent chat for a session."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="messages")


class KBDocument(Base):
    """Metadata record for each document ingested into the knowledge base."""
    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    product: Mapped[str | None] = mapped_column(String(255))
    product_version: Mapped[str | None] = mapped_column(String(50))
    doc_date: Mapped[str | None] = mapped_column(String(20))  # ISO date string
    reuse_permitted: Mapped[bool] = mapped_column(Boolean, default=True)
    redacted: Mapped[bool] = mapped_column(Boolean, default=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FormatRule(Base):
    """Extracted formatting rules for a session, stored as JSON."""
    __tablename__ = "format_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False, unique=True)
    rules_json: Mapped[str] = mapped_column(Text, default="{}")
    confirmed_by_se: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class LLMCall(Base):
    """Audit log of every LLM call — used for AI Disclosure reporting."""
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    session_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
