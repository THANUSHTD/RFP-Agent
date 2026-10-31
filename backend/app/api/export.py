"""
api/export.py — Response package export endpoints (DOCX proposal & XLSX Compliance Matrix).

Generates:
- Formatted DOCX response document following extracted RFP format rules,
  stamped with [APPROVED BY SALES ENGINEER] or [DRAFT — NOT APPROVED].
- Section 7 XLSX Compliance Matrix with color-coded compliance status.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import get_db
from backend.app.models import Session as SessionModel
from backend.app.schemas import ExportPackageOut
from backend.app.services.exporter import (
    EXPORTS_BASE_DIR,
    export_session_package,
)

router = APIRouter(prefix="/sessions", tags=["export"])


@router.post("/{session_id}/export", response_model=ExportPackageOut)
async def export_session(session_id: int, db: AsyncSession = Depends(get_db)) -> ExportPackageOut:
    """Generate both DOCX proposal and XLSX compliance matrix for a session."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        package = await export_session_package(session_id, db)
        return ExportPackageOut(**package)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate export package: {exc}")


@router.get("/{session_id}/export/docx")
async def download_docx(session_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    """Download the formatted DOCX proposal document."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session_dir = EXPORTS_BASE_DIR / str(session_id)
    docx_files = list(session_dir.glob("*.docx")) if session_dir.exists() else []
    if not docx_files:
        # Generate on the fly if not yet generated
        package = await export_session_package(session_id, db)
        docx_path = Path(package["docx_path"])
    else:
        docx_path = docx_files[0]

    return FileResponse(
        path=str(docx_path),
        filename=docx_path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/{session_id}/export/xlsx")
async def download_xlsx(session_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    """Download the Section 7 XLSX Compliance Matrix spreadsheet."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session_dir = EXPORTS_BASE_DIR / str(session_id)
    xlsx_files = list(session_dir.glob("*.xlsx")) if session_dir.exists() else []
    if not xlsx_files:
        # Generate on the fly if not yet generated
        package = await export_session_package(session_id, db)
        xlsx_path = Path(package["xlsx_path"])
    else:
        xlsx_path = xlsx_files[0]

    return FileResponse(
        path=str(xlsx_path),
        filename=xlsx_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
