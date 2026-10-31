"""
generate_sample_rfp.py — Creates data/sample_rfp/sample_rfp.docx and .pdf

Islamic Banking RFP — SAMPLE document for testing the RFP Agent.
~30 questions covering: Murabaha, Ijarah, Musharakah, Sukuk, Shariah governance,
technical architecture, commercial/legal (flagged), and gap questions (clarifications).

All content is SYNTHETIC. No real data.
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

OUTPUT_DIR = Path("data/sample_rfp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_docx() -> Path:
    doc = Document()

    # ── Title ──────────────────────────────────────────────────────────────
    t = doc.add_heading("REQUEST FOR PROPOSAL (RFP)", 0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = doc.add_paragraph("Islamic Lending & Finance Platform")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.runs[0].bold = True
    sub.runs[0].font.size = Pt(16)

    warn = doc.add_paragraph(
        "SAMPLE DOCUMENT — All names, figures and requirements are synthetic. For testing only."
    )
    warn.alignment = WD_ALIGN_PARAGRAPH.CENTER
    warn.runs[0].font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
    warn.runs[0].bold = True

    doc.add_paragraph()
    for label, value in [
        ("Issuing Organisation", "Al-Baraka Digital Bank (SAMPLE)"),
        ("RFP Reference", "ABDB-RFP-2024-001"),
        ("Issue Date", "1 November 2024"),
        ("Response Deadline", "30 November 2024, 17:00 GST"),
        ("Contact", "rfp@al-baraka-sample.example  [SAMPLE — do not email]"),
        ("Document Version", "1.0"),
    ]:
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(value)

    doc.add_page_break()

    # ── Section 1 ──────────────────────────────────────────────────────────
    doc.add_heading("1. Introduction and Background", 1)
    doc.add_paragraph(
        "Al-Baraka Digital Bank (SAMPLE) is a Shariah-compliant digital bank seeking "
        "a comprehensive Islamic Lending and Finance Platform to support its retail and "
        "corporate banking operations. The platform must support Murabaha, Ijarah, "
        "Musharakah, Tawarruq, and Sukuk-related products in full compliance with "
        "AAOIFI standards and local regulatory requirements."
    )

    # ── Section 2: Format rules ────────────────────────────────────────────
    doc.add_heading("2. Response Formatting Instructions", 1)
    rules = [
        "Numbering: Use the question numbering exactly as given (e.g. 3.1, 3.2.1).",
        "Word limit: Maximum 250 words per narrative answer.",
        "Section headings: Each answer must begin with the question number and a short heading.",
        "File naming: ABDB-RFP-2024-001_<VendorName>_Response.docx",
        "Language: English only. Formal business tone.",
        "Compliance matrix: Complete Section 7 in the provided XLSX template.",
        "Mandatory items: All [MANDATORY] questions must be answered.",
        "Pricing: Submit in a separate sealed document (not in this file).",
    ]
    for rule in rules:
        doc.add_paragraph(rule, style="List Bullet")

    doc.add_page_break()

    # ── Helper ─────────────────────────────────────────────────────────────
    def q(num, text, mandatory=True, note=""):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        r = p.add_run(f"{num}.  ")
        r.bold = True
        p.add_run(text)
        tag = "  [MANDATORY]" if mandatory else "  [OPTIONAL]"
        p.add_run(tag).bold = True
        if note:
            p.add_run(f"\n    ↳ Note: {note}")

    # ── Section 3: Core capabilities ──────────────────────────────────────
    doc.add_heading("3. Core Platform Capabilities", 1)

    doc.add_heading("3.1 Murabaha Financing", 2)
    q(
        "3.1.1",
        "Describe how your platform supports Murabaha cost-plus financing, including "
        "profit calculation method, deferred payment scheduling, and disclosure of cost "
        "and profit margin to the customer.",
        mandatory=True,
    )
    q(
        "3.1.2",
        "Does your platform support Commodity Murabaha (Tawarruq) structures? Describe "
        "the commodity procurement workflow and how Shariah compliance is maintained "
        "throughout the transaction lifecycle.",
        mandatory=True,
    )
    q(
        "3.1.3",
        "How does the platform handle early settlement of Murabaha contracts? Does it "
        "support voluntary rebates (Ibra) and how is this configured?",
        mandatory=True,
    )

    doc.add_heading("3.2 Ijarah (Leasing)", 2)
    q(
        "3.2.1",
        "Describe your platform's support for Ijarah (operating lease) and Ijarah "
        "Muntahia Bittamleek (lease-to-own). Include asset registration, depreciation "
        "handling, and ownership transfer at end of term.",
        mandatory=True,
    )
    q(
        "3.2.2",
        "How does the platform manage variable rental rates in Ijarah contracts linked "
        "to Islamic benchmark rates?",
        mandatory=False,
    )

    doc.add_heading("3.3 Musharakah", 2)
    q(
        "3.3.1",
        "Describe your platform's support for Diminishing Musharakah (Musharakah "
        "Mutanaqisa) for home financing, including partner share reduction scheduling "
        "and profit distribution calculations.",
        mandatory=True,
    )
    q(
        "3.3.2",
        "How does the system handle Musharakah profit-and-loss sharing when actual "
        "returns differ from projected returns?",
        mandatory=True,
    )

    doc.add_heading("3.4 Sukuk Administration", 2)
    q(
        "3.4.1",
        "Does your platform support Sukuk issuance and administration? Describe "
        "supported structures (Ijarah Sukuk, Murabaha Sukuk) and investor profit "
        "distribution workflow.",
        mandatory=False,
    )
    q(
        "3.4.2",
        "How does the platform integrate with central securities depositories (CSDs) "
        "for Sukuk settlement and custody?",
        mandatory=False,
        note="If not supported natively, describe the integration approach.",
    )

    doc.add_page_break()

    # ── Section 4: Shariah Governance ─────────────────────────────────────
    doc.add_heading("4. Shariah Governance and Compliance", 1)
    q(
        "4.1",
        "Describe the Shariah governance workflow in your platform. How are new products "
        "submitted for Shariah Board approval, and how are approved fatwas stored and "
        "linked to product configurations?",
        mandatory=True,
    )
    q(
        "4.2",
        "How does the platform generate AAOIFI-compliant financial statements and Shariah "
        "audit reports? List the specific AAOIFI FAS standards your reporting covers.",
        mandatory=True,
    )
    q(
        "4.3",
        "Does the platform include a Shariah non-compliance detection mechanism? Describe "
        "how prohibited transactions (riba, gharar, maysir) are flagged and escalated.",
        mandatory=True,
    )
    q(
        "4.4",
        "What is your approach to Zakat calculation and reporting for eligible accounts? "
        "Is this configurable per jurisdiction?",
        mandatory=False,
    )

    doc.add_page_break()

    # ── Section 5: Technical Architecture ────────────────────────────────
    doc.add_heading("5. Technical Architecture and Integration", 1)
    q(
        "5.1",
        "Provide an overview of your platform's technical architecture, including "
        "deployment models (cloud, on-premise, hybrid), technology stack, and "
        "high-availability design.",
        mandatory=True,
    )
    q(
        "5.2",
        "What APIs does your platform expose for integration with core banking systems? "
        "Do you support REST and ISO 20022 messaging?",
        mandatory=True,
    )
    q(
        "5.3",
        "Describe your data security architecture: encryption at rest and in transit, "
        "access control model, and key management.",
        mandatory=True,
    )
    q(
        "5.4",
        "Does the platform support multi-currency and multi-entity operations? Describe "
        "currency conversion handling for cross-border Islamic finance.",
        mandatory=True,
    )
    q(
        "5.5",
        "What is the platform's approach to regulatory reporting for GCC-region central "
        "banks (CBUAE, SAMA)? List supported report formats.",
        mandatory=False,
        note="If not standard, describe custom options available.",
    )
    q(
        "5.6",
        "Describe AI/ML capabilities for credit scoring or fraud detection in an Islamic "
        "finance context.",
        mandatory=False,
        note="If not available, describe your product roadmap.",
    )

    doc.add_page_break()

    # ── Section 6: Commercial / SLA / Legal (owner-flagged) ───────────────
    doc.add_heading("6. Commercial Terms, SLA and Legal", 1)
    doc.add_paragraph(
        "NOTICE: Responses to this section are reviewed by Procurement, Legal, and Compliance. "
        "Answers must be from authorised representatives."
    ).runs[0].bold = True

    q(
        "6.1",
        "Provide total cost of ownership (TCO) for a 5-year engagement including "
        "implementation fees, annual licence, and support costs.",
        mandatory=True,
        note="[PRICING] — Submit in a separate sealed pricing document. Do NOT include here.",
    )
    q(
        "6.2",
        "State your standard SLA commitments for platform uptime, incident response, "
        "and disaster recovery RTO/RPO.",
        mandatory=True,
        note="[SLA] — Requires review by Delivery and Legal teams.",
    )
    q(
        "6.3",
        "Confirm whether your contract includes data residency guarantees for UAE-hosted "
        "deployments and whether you accept DIFC law as governing law.",
        mandatory=True,
        note="[LEGAL] — Requires Legal team review. Do not auto-answer.",
    )

    doc.add_page_break()

    # ── Section 7: Compliance Matrix ──────────────────────────────────────
    doc.add_heading("7. Compliance Matrix", 1)
    doc.add_paragraph(
        "For each row enter: Compliant / Partially Compliant / Non-Compliant / Roadmap. "
        "Reference the section of your response that supports the claim."
    )

    tbl = doc.add_table(rows=1, cols=5)
    tbl.style = "Table Grid"
    hdrs = ["Req ID", "Requirement", "Mandatory", "Vendor Response", "Reference"]
    for i, h in enumerate(hdrs):
        tbl.rows[0].cells[i].text = h
        tbl.rows[0].cells[i].paragraphs[0].runs[0].bold = True

    matrix = [
        ("CM-01", "Murabaha financing with AAOIFI-compliant profit disclosure", "Yes"),
        ("CM-02", "Commodity Murabaha (Tawarruq) workflow", "Yes"),
        ("CM-03", "Ijarah operating lease product", "Yes"),
        ("CM-04", "Ijarah Muntahia Bittamleek (lease-to-own)", "Yes"),
        ("CM-05", "Diminishing Musharakah for home financing", "Yes"),
        ("CM-06", "Sukuk administration and investor distribution", "Optional"),
        ("CM-07", "Shariah Board approval workflow", "Yes"),
        ("CM-08", "AAOIFI FAS-compliant financial reporting", "Yes"),
        ("CM-09", "Multi-currency and multi-entity support", "Yes"),
        ("CM-10", "REST API for core banking integration", "Yes"),
        ("CM-11", "ISO 20022 messaging", "Optional"),
        ("CM-12", "Encryption at rest (AES-256 or equivalent)", "Yes"),
        ("CM-13", "Role-based access control (RBAC)", "Yes"),
        ("CM-14", "GCC regulatory reporting (CBUAE / SAMA)", "Optional"),
        ("CM-15", "Zakat calculation and reporting", "Optional"),
        ("CM-16", "AI/ML credit scoring", "Optional"),
        ("CM-17", "DIFC / UAE data residency guarantee", "Yes"),
        ("CM-18", "DR: RTO <= 4 hours, RPO <= 1 hour", "Yes"),
    ]
    for req_id, requirement, mand in matrix:
        row = tbl.add_row()
        row.cells[0].text = req_id
        row.cells[1].text = requirement
        row.cells[2].text = mand
        row.cells[3].text = ""
        row.cells[4].text = ""

    doc.add_page_break()

    # ── Section 8: Implementation ──────────────────────────────────────────
    doc.add_heading("8. Implementation and Support", 1)
    q(
        "8.1",
        "Describe your implementation methodology for a greenfield Islamic bank deployment. "
        "What is the typical timeline and how is project governance structured?",
        mandatory=True,
    )
    q(
        "8.2",
        "What is your approach to data migration from legacy Islamic banking systems? "
        "Describe tools and validation processes used.",
        mandatory=True,
        note="This topic may not be in standard documentation — provide full details.",
    )
    q(
        "8.3",
        "Do you offer dedicated Shariah-qualified technical consultants as part of the "
        "implementation team? What certifications do they hold?",
        mandatory=False,
        note="Gap question — may become a clarification item.",
    )
    q(
        "8.4",
        "How is user training delivered? Do you provide e-learning modules in Arabic? "
        "What is the trainer-to-user ratio for classroom sessions?",
        mandatory=False,
        note="Gap question — similar intent to 8.3 (dedup test).",
    )

    # ── Section 9: References ──────────────────────────────────────────────
    doc.add_heading("9. Vendor References", 1)
    q(
        "9.1",
        "Provide three references from Islamic bank deployments completed in the last "
        "five years (bank name, country, scope, contact).",
        mandatory=True,
        note="Gap question — not answerable from product docs.",
    )
    q(
        "9.2",
        "How many live AAOIFI-certified Islamic banking clients do you currently serve? "
        "Describe your experience with AAOIFI deployments.",
        mandatory=True,
    )

    # ── End ────────────────────────────────────────────────────────────────
    doc.add_page_break()
    end = doc.add_paragraph(
        "END OF RFP\n\n"
        "SAMPLE — Al-Baraka Digital Bank (fictional). All requirements, names, and figures "
        "are synthetic. Reference: ABDB-RFP-2024-001 v1.0"
    )
    end.alignment = WD_ALIGN_PARAGRAPH.CENTER

    out = OUTPUT_DIR / "sample_rfp.docx"
    doc.save(str(out))
    return out


def build_pdf(docx_path: Path) -> Path:
    """Convert DOCX to a readable PDF via PyMuPDF text rendering."""
    import fitz

    pdf = fitz.open()
    existing = Document(str(docx_path))

    W, H = 595, 842  # A4 points
    MARGIN_X, MARGIN_Y = 50, 55
    LINE_SPACING = 4

    current_page = pdf.new_page(width=W, height=H)
    y = MARGIN_Y

    def ensure_space(needed: int) -> None:
        nonlocal current_page, y
        if y + needed > H - MARGIN_Y:
            current_page = pdf.new_page(width=W, height=H)
            y = MARGIN_Y

    def draw_text(text: str, fontsize: int, bold: bool = False, color=(0, 0, 0)) -> None:
        nonlocal y
        fontname = "Courier" if bold else "Courier"  # helv not always available
        fontname = "helv"
        max_chars = max(1, int((W - 2 * MARGIN_X) / (fontsize * 0.52)))
        words = text.split()
        line, lines = "", []
        for w in words:
            candidate = (line + " " + w).strip()
            if len(candidate) <= max_chars:
                line = candidate
            else:
                lines.append(line)
                line = w
        if line:
            lines.append(line)
        for ln in lines:
            ensure_space(fontsize + LINE_SPACING)
            current_page.insert_text(
                (MARGIN_X, y), ln, fontsize=fontsize, fontname=fontname, color=color
            )
            y += fontsize + LINE_SPACING
        y += 2

    for para in existing.paragraphs:
        text = para.text.strip()
        if not text:
            y += 5
            continue
        style = para.style.name
        if "Title" in style or "Heading 1" in style:
            draw_text(text, 13, bold=True)
        elif "Heading 2" in style:
            draw_text(text, 11, bold=True)
        elif "Heading 3" in style:
            draw_text(text, 10, bold=True)
        elif "List" in style:
            draw_text("• " + text, 9)
        else:
            draw_text(text, 9)

    # Tables
    for tbl in existing.tables:
        for row in tbl.rows:
            row_text = " | ".join(c.text.strip() for c in row.cells)
            if row_text.strip():
                draw_text(row_text[:120], 8)

    out = OUTPUT_DIR / "sample_rfp.pdf"
    pdf.save(str(out))
    return out


if __name__ == "__main__":
    print("Building DOCX...")
    docx_path = build_docx()
    print(f"  Saved: {docx_path}")

    print("Building PDF...")
    pdf_path = build_pdf(docx_path)
    print(f"  Saved: {pdf_path}")

    print("\nDone. Files in data/sample_rfp/")
