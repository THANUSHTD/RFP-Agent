"""
backend/app/services/exporter.py — Export generation service for DOCX response documents
and XLSX Compliance Matrices.

Rules Enforced:
1. Exact section hierarchy & question numbering based on extracted format rules.
2. Prominent [DRAFT — NOT APPROVED] stamp on any answer not confirmed by SE.
3. Explicit [APPROVED] stamp with approval timestamp on SE-confirmed responses.
4. Department routing callouts for commercial, legal, and SLA questions.
5. All citations and staleness notices included.
6. Openpyxl Section 7 compliance matrix with formatted headers, auto-width, and status color codes.
"""

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import openpyxl
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches, Pt, RGBColor
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Answer,
    FormatRule,
    Question,
    Section,
)
from backend.app.models import (
    Session as SessionModel,
)

logger = logging.getLogger(__name__)

EXPORTS_BASE_DIR = Path("exports")


def _set_cell_background(cell: Any, fill_hex: str) -> None:
    """Set background color of a DOCX table cell using XML shading."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex.lstrip("#")}"/>')
    tc_pr.append(shd)


def _add_horizontal_rule(doc: Document) -> None:
    """Add a subtle horizontal border line in DOCX."""
    p = doc.add_paragraph()
    p_pr = p._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom_bdr = parse_xml(
        f'<w:bottom {nsdecls("w")} w:val="single" w:sz="6" w:space="1" w:color="CBD5E1"/>'
    )
    p_bdr.append(bottom_bdr)
    p_pr.append(p_bdr)


async def generate_docx_export(
    session_id: int,
    db: AsyncSession,
    output_path: Path,
) -> Path:
    """Generate professional DOCX response document following RFP formatting guidelines."""
    # 1. Fetch Session, Rules, Sections, and Questions with Answers
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    format_rule_res = await db.execute(
        select(FormatRule).where(FormatRule.session_id == session_id)
    )
    format_rule = format_rule_res.scalar_one_or_none()
    rules: dict[str, Any] = {}
    if format_rule and format_rule.rules_json:
        try:
            rules = json.loads(format_rule.rules_json)
        except Exception:
            rules = {}

    sec_res = await db.execute(
        select(Section)
        .join(Question, Question.section_id == Section.id)
        .where(Question.session_id == session_id)
        .distinct()
        .order_by(Section.order_index)
    )
    sections = list(sec_res.scalars())

    q_res = await db.execute(
        select(Question).where(Question.session_id == session_id).order_by(Question.id)
    )
    all_questions = list(q_res.scalars())

    # Map question_id to latest Answer
    ans_res = await db.execute(
        select(Answer)
        .join(Question, Question.id == Answer.question_id)
        .where(Question.session_id == session_id)
        .order_by(Answer.version.desc())
    )
    all_answers = list(ans_res.scalars())
    latest_answers: dict[int, Answer] = {}
    for a in all_answers:
        if a.question_id not in latest_answers:
            latest_answers[a.question_id] = a

    # 2. Build Document
    doc = Document()

    # Document Geometry / Margins
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # ── Title Page ────────────────────────────────────────────────────────────
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(72)
    title_p.paragraph_format.space_after = Pt(12)
    title_run = title_p.add_run("RFP RESPONSE PROPOSAL")
    title_run.font.name = "Calibri"
    title_run.font.size = Pt(28)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)  # Navy Blue

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(36)
    sub_run = sub_p.add_run("AzentioFinance — Islamic Banking & Lending Solution")
    sub_run.font.name = "Calibri"
    sub_run.font.size = Pt(16)
    sub_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

    meta_table = doc.add_table(rows=5, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    meta_rows = [
        ("Project / RFP Session:", session.name),
        ("Prepared By:", "Azentio Sales Engineering & Solution Architecture"),
        ("Date Generated:", datetime.now(UTC).strftime("%B %d, %Y (%H:%M UTC)")),
        ("Product Architecture:", "AzentioFinance Core v3.0 (Cloud Native / AAOIFI Certified)"),
        ("Classification:", "CONFIDENTIAL & PROPRIETARY — PREPARED FOR PROSPECT EVALUATION"),
    ]
    for row_idx, (lbl, val) in enumerate(meta_rows):
        r = meta_table.rows[row_idx]
        lbl_p = r.cells[0].paragraphs[0]
        lbl_p.add_run(lbl).font.bold = True
        r.cells[1].paragraphs[0].add_run(val)

    doc.add_page_break()

    # ── Executive Summary & Overview ──────────────────────────────────────────
    h1 = doc.add_heading("Executive Summary", level=1)
    h1.paragraph_format.space_before = Pt(18)
    h1.paragraph_format.space_after = Pt(8)

    exec_p = doc.add_paragraph(
        "Azentio Software is pleased to submit this comprehensive proposal in response to your Request for "
        "Proposal (RFP). Our solution is architected natively on modern, cloud-first principles and adheres "
        "rigorously to AAOIFI (Accounting and Auditing Organization for Islamic Financial Institutions) standards "
        "for Shariah-compliant financing and lending operations.\n\n"
        "This response document details our core capabilities across Murabaha, Ijarah, Mudaraba, Musharaka, "
        "Istisna'a, and Tawarruq financing, supported by automated dual-entry Islamic accounting, dual-calendar "
        "schedules, and comprehensive Shariah Supervisory Board audit trails."
    )
    exec_p.paragraph_format.space_after = Pt(16)

    # Summary Statistics Table
    total_q = len(all_questions)
    approved_q = sum(
        1
        for q in all_questions
        if latest_answers.get(q.id) and latest_answers[q.id].status == "approved"
    )
    draft_q = total_q - approved_q

    stat_table = doc.add_table(rows=2, cols=4)
    stat_table.style = "Table Grid"
    headers = ["Total Requirements", "SE Approved", "Draft Answers", "Format Rules Enforced"]
    values = [
        str(total_q),
        f"{approved_q} ({int(approved_q/total_q*100 if total_q else 0)}%)",
        str(draft_q),
        "Yes (Confirmed)" if format_rule and format_rule.confirmed_by_se else "Detected",
    ]

    for col_idx, (h_text, v_text) in enumerate(zip(headers, values, strict=False)):
        h_cell = stat_table.cell(0, col_idx)
        _set_cell_background(h_cell, "#1E3A8A")
        h_run = h_cell.paragraphs[0].add_run(h_text)
        h_run.font.bold = True
        h_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        v_cell = stat_table.cell(1, col_idx)
        _set_cell_background(v_cell, "#F8FAFC")
        v_run = v_cell.paragraphs[0].add_run(v_text)
        v_run.font.bold = True
        v_run.font.size = Pt(13)

    doc.add_paragraph().paragraph_format.space_after = Pt(18)

    # ── Questions by Section ──────────────────────────────────────────────────
    # Group questions by section
    section_map: dict[int | None, list[Question]] = {}
    for q in all_questions:
        section_map.setdefault(q.section_id, []).append(q)

    # Include sections that exist, plus any questions without section
    sections_to_render = list(sections)
    if None in section_map and section_map[None]:
        dummy_sec = Section(id=-1, title="General Requirements", order_index=999)
        sections_to_render.append(dummy_sec)

    include_headings = rules.get("section_headings", True)

    for sec in sections_to_render:
        q_list = section_map.get(sec.id if sec.id != -1 else None, [])
        if not q_list:
            continue

        if include_headings:
            sec_heading = doc.add_heading(sec.title, level=1)
            sec_heading.paragraph_format.space_before = Pt(20)
            sec_heading.paragraph_format.space_after = Pt(8)

        for q in q_list:
            ans = latest_answers.get(q.id)
            is_approved = ans is not None and ans.status == "approved"

            # Question Header
            q_p = doc.add_paragraph()
            q_p.paragraph_format.space_before = Pt(12)
            q_p.paragraph_format.space_after = Pt(4)
            q_num_run = q_p.add_run(f"Requirement {q.number}: ")
            q_num_run.font.bold = True
            q_num_run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

            q_text_run = q_p.add_run(q.text)
            q_text_run.font.bold = True

            # Approval Status Banner / Callout
            status_p = doc.add_paragraph()
            status_p.paragraph_format.space_after = Pt(6)

            if is_approved:
                appr_run = status_p.add_run("✅ [APPROVED BY SALES ENGINEER]")
                appr_run.font.bold = True
                appr_run.font.color.rgb = RGBColor(0x16, 0x65, 0x34)  # Forest Green
                if ans.approved_at:
                    appr_time = ans.approved_at.strftime("%Y-%m-%d %H:%M UTC")
                    status_p.add_run(
                        f" — Confirmed at {appr_time} (v{ans.version})"
                    ).font.size = Pt(9)
            elif q.owner:
                owner_run = status_p.add_run(
                    f"🏷️ [ASSIGNED TO {q.owner.upper()} — PENDING DEPARTMENT INPUT]"
                )
                owner_run.font.bold = True
                owner_run.font.color.rgb = RGBColor(0x9A, 0x34, 0x12)  # Dark Amber
            else:
                draft_run = status_p.add_run("⚠️ [DRAFT — NOT APPROVED BY SALES ENGINEER]")
                draft_run.font.bold = True
                draft_run.font.color.rgb = RGBColor(0xDC, 0x26, 0x26)  # Red warning
                status_p.add_run(
                    " — Automated preliminary response subject to Sales Engineering verification."
                ).font.size = Pt(9)

            # Answer Text Box / Callout
            ans_box = doc.add_table(rows=1, cols=1)
            ans_box.alignment = WD_TABLE_ALIGNMENT.LEFT
            ans_box.autofit = False
            ans_cell = ans_box.cell(0, 0)
            ans_cell.width = Inches(6.5)

            if is_approved:
                _set_cell_background(ans_cell, "#F0FDF4")  # Soft green background
            elif q.owner:
                _set_cell_background(ans_cell, "#FFFBEB")  # Soft amber background
            else:
                _set_cell_background(ans_cell, "#FEF2F2")  # Soft red background

            ans_p = ans_cell.paragraphs[0]
            ans_p.paragraph_format.space_before = Pt(4)
            ans_p.paragraph_format.space_after = Pt(4)

            if ans and ans.text.strip():
                # Clean markdown styling for Word
                clean_ans = ans.text.replace("**", "").replace("•", "• ")
                ans_p.add_run(clean_ans)
            else:
                ans_p.add_run(
                    "No drafted response available. Assigned to Sales Engineer for preparation."
                )

            # Citations list
            if ans and ans.citations:
                cite_p = doc.add_paragraph()
                cite_p.paragraph_format.space_before = Pt(4)
                cite_p.paragraph_format.space_after = Pt(8)
                c_lbl = cite_p.add_run("Verified Knowledge Sources & Citations:\n")
                c_lbl.font.size = Pt(8.5)
                c_lbl.font.bold = True
                c_lbl.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

                for c in ans.citations:
                    chunk_id = c.get("chunk_id", "ref")
                    doc_name = c.get("document", "KB Document")
                    snippet = c.get("snippet", "")[:120].strip()
                    c_run = cite_p.add_run(f'  • [{chunk_id}] {doc_name}: "{snippet}..."\n')
                    c_run.font.size = Pt(8)
                    c_run.font.italic = True
                    c_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

            # Staleness notices
            if ans and ans.stale_warnings:
                stale_p = doc.add_paragraph()
                stale_p.paragraph_format.space_before = Pt(2)
                stale_p.paragraph_format.space_after = Pt(8)
                for sw in ans.stale_warnings:
                    s_run = stale_p.add_run(f"⚠️ Staleness Warning: {sw}\n")
                    s_run.font.size = Pt(8.5)
                    s_run.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)

            _add_horizontal_rule(doc)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    logger.info("Saved DOCX export to %s", output_path)
    return output_path


async def generate_xlsx_matrix(
    session_id: int,
    db: AsyncSession,
    output_path: Path,
) -> Path:
    """Generate professional Section 7 XLSX Compliance Matrix with color-coded status."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    # Fetch questions and sections
    q_res = await db.execute(
        select(Question).where(Question.session_id == session_id).order_by(Question.id)
    )
    questions = list(q_res.scalars())

    sec_res = await db.execute(
        select(Section)
        .join(Question, Question.section_id == Section.id)
        .where(Question.session_id == session_id)
        .distinct()
    )
    sections_by_id = {s.id: s.title for s in sec_res.scalars()}

    # Fetch latest answers
    ans_res = await db.execute(
        select(Answer)
        .join(Question, Question.id == Answer.question_id)
        .where(Question.session_id == session_id)
        .order_by(Answer.version.desc())
    )
    latest_answers: dict[int, Answer] = {}
    for a in ans_res.scalars():
        if a.question_id not in latest_answers:
            latest_answers[a.question_id] = a

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Compliance Matrix"
    ws.views.sheetView[0].showGridLines = True

    # ── Header Title Block ────────────────────────────────────────────────────
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.value = "AzentioFinance — RFP Compliance & Requirement Matrix"
    title_cell.font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
    title_cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:I2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Project: {session.name} | Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} | Confidential"
    sub_cell.font = Font(name="Calibri", size=10, italic=True, color="64748B")
    sub_cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 18

    # Empty spacer row
    ws.row_dimensions[3].height = 10

    # ── Column Headers (Row 4) ────────────────────────────────────────────────
    headers = [
        "Item No.",
        "Section",
        "Requirement / Question",
        "Category",
        "Compliance Status",
        "Assigned Owner",
        "SE Approved",
        "Confidence",
        "Proposed Solution & Compliance Notes",
    ]

    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    ws.row_dimensions[4].height = 26
    for col_idx, h_text in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h_text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # Freeze header rows
    ws.freeze_panes = "A5"

    # Status color fills
    compliant_fill = PatternFill(
        start_color="D1FAE5", end_color="D1FAE5", fill_type="solid"
    )  # Green
    compliant_font = Font(name="Calibri", size=10, bold=True, color="065F46")

    draft_fill = PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid")  # Cyan
    draft_font = Font(name="Calibri", size=10, bold=True, color="0369A1")

    clarif_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")  # Amber
    clarif_font = Font(name="Calibri", size=10, bold=True, color="92400E")

    flagged_fill = PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid")  # Rose
    flagged_font = Font(name="Calibri", size=10, bold=True, color="9F1239")

    # ── Populate Data Rows ────────────────────────────────────────────────────
    row_idx = 5
    for q in questions:
        ans = latest_answers.get(q.id)
        is_approved = ans is not None and ans.status == "approved"
        sec_title = sections_by_id.get(q.section_id, "General Requirements")

        # Determine compliance status string and style
        if is_approved:
            compliance_str = "Compliant (Approved)"
            c_fill, c_font = compliant_fill, compliant_font
            approved_str = "Yes ✅"
        elif q.owner:
            compliance_str = f"Pending ({q.owner})"
            c_fill, c_font = flagged_fill, flagged_font
            approved_str = "No (Flagged)"
        elif ans and ans.status == "draft":
            compliance_str = "Compliant (Draft)"
            c_fill, c_font = draft_fill, draft_font
            approved_str = "No (Draft)"
        else:
            compliance_str = "Clarification Needed"
            c_fill, c_font = clarif_fill, clarif_font
            approved_str = "No"

        conf_str = f"{int(ans.confidence * 100)}%" if ans else "—"
        sol_notes = ans.text if ans else "Assigned to Sales Engineer for authoring."
        # Strip long markdown bold/header markers for clean spreadsheet view
        sol_notes_clean = re.sub(r"[*#]", "", sol_notes).strip()

        row_data = [
            q.number,
            sec_title,
            q.text,
            q.category.upper(),
            compliance_str,
            q.owner or "Sales Engineering",
            approved_str,
            conf_str,
            sol_notes_clean,
        ]

        ws.row_dimensions[row_idx].height = 42
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border
            cell.font = Font(name="Calibri", size=10)

            # Center alignment for metadata columns
            if col_idx in (1, 4, 6, 7, 8):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in (2, 3, 9):
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

            # Apply status color to Column 5 (Compliance Status)
            if col_idx == 5:
                cell.fill = c_fill
                cell.font = c_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

        row_idx += 1

    # ── Set Column Widths ─────────────────────────────────────────────────────
    col_widths = {
        1: 12,  # Item No
        2: 24,  # Section
        3: 40,  # Requirement
        4: 14,  # Category
        5: 22,  # Compliance Status
        6: 18,  # Assigned Owner
        7: 14,  # SE Approved
        8: 13,  # Confidence
        9: 60,  # Solution Notes
    }
    for col_idx, width in col_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    logger.info("Saved XLSX matrix export to %s", output_path)
    return output_path


async def export_session_package(session_id: int, db: AsyncSession) -> dict[str, Any]:
    """Build both DOCX and XLSX export artifacts for the session."""
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    session_export_dir = EXPORTS_BASE_DIR / str(session_id)
    session_export_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^\w\-]", "_", session.name)
    docx_file = session_export_dir / f"RFP_Response_{safe_name}.docx"
    xlsx_file = session_export_dir / f"Compliance_Matrix_{safe_name}.xlsx"

    await generate_docx_export(session_id, db, docx_file)
    await generate_xlsx_matrix(session_id, db, xlsx_file)

    q_res = await db.execute(select(Question).where(Question.session_id == session_id))
    questions = list(q_res.scalars())

    ans_res = await db.execute(
        select(Answer)
        .join(Question, Question.id == Answer.question_id)
        .where(Question.session_id == session_id, Answer.status == "approved")
    )
    approved_count = len(list(ans_res.scalars()))

    return {
        "session_id": session_id,
        "session_name": session.name,
        "docx_path": str(docx_file),
        "xlsx_path": str(xlsx_file),
        "docx_filename": docx_file.name,
        "xlsx_filename": xlsx_file.name,
        "total_questions": len(questions),
        "approved_count": approved_count,
        "generated_at": datetime.now(UTC).isoformat(),
    }
