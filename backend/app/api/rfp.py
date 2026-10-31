"""
api/rfp.py — RFP document upload and analysis endpoints.

Upload validates file type and size. Analysis is a stub in Phase 0;
the full LangGraph pipeline is wired up in Phase 2/3.
"""
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db import get_db
from backend.app.models import RFPDocument
from backend.app.models import Session as SessionModel
from backend.app.schemas import OKResponse, RFPDocumentOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sessions", tags=["rfp"])
settings = get_settings()

ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
UPLOAD_DIR = Path("uploads")


def _sanitise_filename(name: str) -> str:
    """Remove dangerous characters from uploaded filenames."""
    # Keep only alphanumerics, dots, dashes, underscores, spaces
    return re.sub(r"[^\w\s.\-]", "_", name)


@router.post(
    "/{session_id}/rfp",
    response_model=RFPDocumentOut,
    status_code=201,
    summary="Upload RFP document",
)
async def upload_rfp(
    session_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> RFPDocumentOut:
    """Upload an RFP PDF or DOCX to an existing session.

    Validates:
    - Session exists
    - File content type is PDF or DOCX
    - File size <= MAX_UPLOAD_MB
    """
    # 1. Check session exists
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Validate content type or file extension
    ext = Path(file.filename or "").suffix.lower()
    is_valid = file.content_type in ALLOWED_TYPES or ext in (".pdf", ".docx")
    if not is_valid:
        raise HTTPException(
            status_code=415,
            detail="Only PDF and DOCX files are accepted.",
        )


    # 3. Read and check size
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_mb} MB limit.",
        )

    # 4. Sanitise filename and save
    safe_name = _sanitise_filename(file.filename or "upload")
    session_dir = UPLOAD_DIR / str(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    dest = session_dir / safe_name
    dest.write_bytes(data)

    # 5. Determine file type
    file_type = "pdf" if file.content_type == "application/pdf" else "docx"

    # 6. Persist document record
    doc = RFPDocument(
        session_id=session_id,
        filename=safe_name,
        file_path=str(dest),
        file_type=file_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    logger.info("Uploaded RFP doc id=%d session=%d file=%s", doc.id, session_id, safe_name)
    return RFPDocumentOut.model_validate(doc)


@router.post(
    "/{session_id}/analyze",
    response_model=OKResponse,
    summary="Trigger LangGraph RFP analysis and answer drafting pipeline",
)
async def analyze_rfp(
    session_id: int,
    db: AsyncSession = Depends(get_db),
) -> OKResponse:
    """Execute LangGraph pipeline: parse structure, extract questions, detect format rules, and draft answers."""
    from backend.app.agents.analyze_graph import analysis_graph

    state = await analysis_graph.ainvoke({"session_id": session_id})
    summary = state.get("summary", {})
    draft_summary = state.get("draft_summary", {})

    return OKResponse(
        message=(
            f"Analysis complete: {summary.get('total_questions', 0)} questions processed. "
            f"Drafted: {draft_summary.get('answered', 0)} answers, "
            f"{draft_summary.get('clarifications', 0)} clarifications, "
            f"{draft_summary.get('flagged', 0)} flagged to department owners."
        )
    )


