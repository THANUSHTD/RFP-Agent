"""
schemas.py — Pydantic v2 request / response schemas.

These are separate from the SQLAlchemy ORM models (models.py).
They define the API contract and are used for validation and serialisation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Shared ───────────────────────────────────────────────────────────────────


class OKResponse(BaseModel):
    ok: bool = True
    message: str = "success"


# ── Sessions ──────────────────────────────────────────────────────────────────


class SessionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


# ── RFP Documents ─────────────────────────────────────────────────────────────


class RFPDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    filename: str
    file_type: str
    uploaded_at: datetime
    analyzed: bool


# ── Questions ─────────────────────────────────────────────────────────────────


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    section_id: int | None
    number: str
    text: str
    mandatory: bool
    kind: str
    category: str
    status: str
    owner: str | None
    created_at: datetime


# ── Answers ───────────────────────────────────────────────────────────────────


class CitationItem(BaseModel):
    """One citation entry in an answer."""

    chunk_id: str = ""
    document: str = ""
    source_type: str = ""
    snippet: str = ""
    # For SE-supplied facts the type is "se_input"
    type: str = "kb"


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    version: int
    text: str
    confidence: float
    citations_json: str
    stale_warnings_json: str
    status: str
    edited_by_se: bool
    approved_at: datetime | None
    created_at: datetime


class AnswerPatch(BaseModel):
    """Fields an SE can update on an answer."""

    text: str | None = None


class ApproveRequest(BaseModel):
    """Body for the approve endpoint — explicit SE confirmation."""

    confirm: bool = Field(..., description="Must be True for approval to proceed.")


# ── Clarifications ────────────────────────────────────────────────────────────


class ClarificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    text: str
    reason: str
    linked_question_ids_json: str
    status: str
    created_at: datetime


# ── Format Rules ──────────────────────────────────────────────────────────────


class FormatRulesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    rules_json: str
    confirmed_by_se: bool
    updated_at: datetime


class FormatRulesPut(BaseModel):
    rules: dict[str, Any]
    confirmed_by_se: bool = False


# ── Chat ──────────────────────────────────────────────────────────────────────


class ChatMessageIn(BaseModel):
    content: str = Field(..., min_length=1)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime


# ── KB ────────────────────────────────────────────────────────────────────────


class KBDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_name: str
    source_type: str
    product: str | None
    product_version: str | None
    doc_date: str | None
    reuse_permitted: bool
    redacted: bool
    chunk_count: int
    ingested_at: datetime


class KBSearchRequest(BaseModel):
    query: str = Field(..., min_length=2)
    top_k: int = 5
    source_type: str | None = None
    product_version: str | None = None


class KBChunkResult(BaseModel):
    chunk_id: str
    document_name: str
    source_type: str
    product: str | None = None
    product_version: str | None = None
    doc_date: str | None = None
    snippet: str
    score: float
    stale_warning: str | None = None


# ── Analysis progress ─────────────────────────────────────────────────────────


class AnalysisProgressEvent(BaseModel):
    """Emitted via SSE during RFP analysis."""

    event: str  # e.g. "parsing", "extracting", "question_done", "complete", "error"
    message: str
    question_id: int | None = None
    total: int | None = None
    done: int | None = None


class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    db: str
    fast_model: str
    draft_model: str


# ── Export ────────────────────────────────────────────────────────────────────


class ExportPackageOut(BaseModel):
    session_id: int
    session_name: str
    docx_filename: str
    xlsx_filename: str
    docx_path: str
    xlsx_path: str
    total_questions: int
    approved_count: int
    generated_at: str


# ── Compliance / Response Codes ───────────────────────────────────────────────


class QuestionResponseCodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    question_id: int
    code: str
    explanation: str
    estimate: str | None
    attachment_ref: str | None
    validated_by_se: bool
    requires_explanation: bool
    updated_at: datetime


class QuestionResponseCodePut(BaseModel):
    code: str
    explanation: str | None = None
    estimate: str | None = None
    attachment_ref: str | None = None
    validated_by_se: bool = False


class ComplianceMatrixRow(BaseModel):
    question_id: int
    number: str
    text: str
    category: str
    mandatory: bool
    status: str
    owner: str | None
    code: str
    code_label: str
    confidence: float
    explanation: str | None
    requires_explanation: bool
    compliance: str
    compliance_class: str


class ComplianceMatrixOut(BaseModel):
    session_id: int
    total: int
    coded: int
    flagged: int
    not_available: int
    rows: list[ComplianceMatrixRow]


# ── Gap Analysis ──────────────────────────────────────────────────────────────


class GapOut(BaseModel):
    id: int
    session_id: int
    question_id: int
    number: str
    requirement: str
    category: str | None
    mandatory: bool
    gap_type: str
    confirmed_gap: bool
    severity: str
    recommended_owner: str
    details: str
    confidence: float
    status: str
    created_at: datetime


class GapAnalysisOut(BaseModel):
    session_id: int
    total: int
    high_severity: int
    confirmed_gaps: int
    knowledge_gaps: int
    gaps: list[GapOut]


class RegenerateRequest(BaseModel):
    force: bool = False


# ── Response Validation ───────────────────────────────────────────────────────


class ValidationIssueOut(BaseModel):
    id: int
    session_id: int
    question_id: int
    number: str
    requirement: str
    issue_type: str
    detail: str
    severity: str
    resolved: bool
    created_at: datetime


class ValidationOut(BaseModel):
    session_id: int
    total: int
    high_severity: int
    medium_severity: int
    issues: list[ValidationIssueOut]


# ── Submission Checklist ──────────────────────────────────────────────────────


class SubmissionChecklistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    item_key: str
    label: str
    status: str
    done_by: str | None
    done_at: datetime | None


class SubmissionChecklistPut(BaseModel):
    status: str
    done_by: str | None = None


class ChecklistSummary(BaseModel):
    session_id: int
    total: int
    done: int
    pending: int
    percent: int
    items: list[SubmissionChecklistOut]
