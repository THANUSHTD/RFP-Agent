"""
backend/app/services/rfp_extractor.py — RFP structure, question extraction and triage engine.

Extracts:
1. Sections (e.g., Core Capabilities, Shariah Governance, Commercial Terms)
2. Questions with number, clean text, mandatory flag, kind, and category
3. Department owner routing according to hard rules:
   - commercial -> Pricing owner -> flagged_owner
   - legal -> Legal owner -> flagged_owner
   - sla -> Delivery owner -> flagged_owner
4. Format rules (word limits, numbering, file naming, required headings)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from backend.app.models import (
    OwnerDept,
    QuestionCategory,
    QuestionKind,
    QuestionStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractedQuestion:
    number: str
    text: str
    mandatory: bool
    kind: QuestionKind
    category: QuestionCategory
    status: QuestionStatus
    owner: OwnerDept | None
    section_title: str


@dataclass
class ExtractedSection:
    title: str
    order_index: int
    questions: list[ExtractedQuestion] = field(default_factory=list)


# ── Triage & Owner Rules ──────────────────────────────────────────────────────

# Pure vendor commercial / pricing terms (must be routed to Pricing owner)
RE_COMMERCIAL_STRICT = re.compile(
    r"\b(?:tco|total cost of ownership|licence fee|license fee|licensing cost|pricing proposal|commercial terms|commercial proposal|hourly rate|annual amc|professional fee|implementation fee|cost breakdown|vendor fees|payment schedule)\b",
    re.IGNORECASE,
)

# Pure legal terms (must be routed to Legal owner)
RE_LEGAL_STRICT = re.compile(
    r"\b(?:governing law|difc law|jurisdiction|indemnity|indemnification|limitation of liability|data residency guarantee|contractual terms|warranty terms|warranties)\b",
    re.IGNORECASE,
)

# Pure SLA & operational commitments (must be routed to Delivery owner)
RE_SLA_STRICT = re.compile(
    r"\b(?:standard sla|sla commitment|uptime commitment|incident response|rto/rpo|recovery time objective|recovery point objective|severity 1|severity level)\b",
    re.IGNORECASE,
)

RE_SHARIAH = re.compile(
    r"\b(?:sharia|shariah|aaoifi|murabaha|ijarah|musharakah|musharaka|tawarruq|sukuk|fatwa|zakat|halal|riba|gharar|maysir|bursa suq|ibra|charity|cost-plus)\b",
    re.IGNORECASE,
)

RE_TECHNICAL = re.compile(
    r"\b(?:architecture|api|apis|cloud|kubernetes|database|encryption|rest|iso 20022|security|integration|sso|microservice|on-premise|hybrid|multi-currency)\b",
    re.IGNORECASE,
)

RE_FUNCTIONAL = re.compile(
    r"\b(?:workflow|lifecycle|feature|features|loan|disbursement|accounting|settlement|user management|audit trail|reporting|kyc|credit scoring|training|migration)\b",
    re.IGNORECASE,
)


def classify_question(
    text: str, section_title: str = ""
) -> tuple[QuestionCategory, OwnerDept | None, QuestionStatus]:
    """Classify a requirement into functional category and department owner.

    Hard Rules:
    - Commercial -> Owner: Pricing, Status: flagged_owner
    - Legal -> Owner: Legal, Status: flagged_owner
    - SLA -> Owner: Delivery, Status: flagged_owner
    - Shariah / Technical / Functional -> Owner: None, Status: pending
    """
    sec_lower = section_title.lower()
    text_lower = text.lower()
    combined = f"{sec_lower} {text_lower}"

    # Prioritize question text specific keywords
    if RE_LEGAL_STRICT.search(text_lower):
        return (QuestionCategory.legal, OwnerDept.legal, QuestionStatus.flagged_owner)

    if RE_SLA_STRICT.search(text_lower):
        return (QuestionCategory.sla, OwnerDept.delivery, QuestionStatus.flagged_owner)

    if RE_COMMERCIAL_STRICT.search(text_lower):
        return (QuestionCategory.commercial, OwnerDept.pricing, QuestionStatus.flagged_owner)

    # Section-level fallback
    if "commercial" in sec_lower and (
        "fee" in text_lower or "cost" in text_lower or "price" in text_lower or "tco" in text_lower
    ):
        return (QuestionCategory.commercial, OwnerDept.pricing, QuestionStatus.flagged_owner)

    if "legal" in sec_lower and (
        "law" in text_lower
        or "contract" in text_lower
        or "jurisdiction" in text_lower
        or "residency" in text_lower
    ):
        return (QuestionCategory.legal, OwnerDept.legal, QuestionStatus.flagged_owner)

    if "sla" in sec_lower and (
        "uptime" in text_lower
        or "rto" in text_lower
        or "response" in text_lower
        or "commitment" in text_lower
    ):
        return (QuestionCategory.sla, OwnerDept.delivery, QuestionStatus.flagged_owner)

    # 4. Shariah (Product/SE)
    if RE_SHARIAH.search(combined):
        return (QuestionCategory.shariah, None, QuestionStatus.pending)

    # 5. Technical (Product/SE)
    if RE_TECHNICAL.search(combined):
        return (QuestionCategory.technical, None, QuestionStatus.pending)

    # 6. Functional (Product/SE)
    if RE_FUNCTIONAL.search(combined):
        return (QuestionCategory.functional, None, QuestionStatus.pending)

    return (QuestionCategory.other, None, QuestionStatus.pending)


# ── Format Rules Extractor ───────────────────────────────────────────────────


def extract_format_rules(text: str) -> dict[str, Any]:
    """Extract response guidelines and formatting rules from document text."""
    rules: dict[str, Any] = {
        "numbering_scheme": "exact as given (e.g. 3.1.1)",
        "word_limit": None,
        "section_headings": True,
        "file_naming": None,
        "language": "English (formal business tone)",
        "compliance_matrix_required": False,
        "pricing_submission": "separate",
    }

    # Extract word limit (e.g. "Maximum 250 words" or "250 word limit")
    word_limit_match = re.search(
        r"(?:maximum|limit of|max\.?)\s*(\d{2,4})\s*words?", text, re.IGNORECASE
    )
    if not word_limit_match:
        word_limit_match = re.search(
            r"(\d{2,4})\s*words?\s*(?:maximum|limit|per answer)", text, re.IGNORECASE
        )
    if word_limit_match:
        rules["word_limit"] = int(word_limit_match.group(1))

    # Extract file naming convention (e.g. "ABDB-RFP-2024-001_<VendorName>_Response.docx")
    naming_match = re.search(r"File naming:\s*([^\n\r]+)", text, re.IGNORECASE)
    if not naming_match:
        naming_match = re.search(
            r"([A-Z0-9_\-]+\s*<[^>]+>\s*_[A-Za-z0-9_\-\.]+\.(?:docx|pdf))", text
        )
    if naming_match:
        rules["file_naming"] = naming_match.group(1).strip()

    # Check compliance matrix
    if re.search(r"compliance matrix|section 7.*xlsx|provided xlsx template", text, re.IGNORECASE):
        rules["compliance_matrix_required"] = True

    # Check separate pricing instruction
    if re.search(r"pricing.*separate (?:sealed )?document", text, re.IGNORECASE):
        rules["pricing_submission"] = "separate sealed document"

    # Check language / tone
    lang_match = re.search(r"Language:\s*([^\n\r]+)", text, re.IGNORECASE)
    if lang_match:
        rules["language"] = lang_match.group(1).strip()

    return rules


# ── Structure & Questions Extractor ──────────────────────────────────────────


def extract_sections_and_questions(text: str) -> list[ExtractedSection]:
    """Parse raw RFP text into hierarchical sections and discrete questions."""
    lines = text.splitlines()

    # Identify major section boundaries (e.g. "1. Introduction", "3. Core Platform Capabilities")
    section_header_re = re.compile(r"^(?:#{1,3}\s*)?(\d+)\.\s+([A-Za-z0-9,\s&/\-]+)$")

    # Identify questions (e.g. "3.1.1. Describe...", "4.1. Describe...", "6.2. State...")
    question_re = re.compile(r"^(\d+(?:\.\d+)+)\.?\s+(.+)$")

    sections: list[ExtractedSection] = []
    current_section = ExtractedSection(title="General Requirements", order_index=0)
    current_question: ExtractedQuestion | None = None

    order_counter = 1

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue

        # Check for top-level section header
        sec_match = section_header_re.match(line_str)
        if sec_match:
            sec_num, sec_name = sec_match.group(1), sec_match.group(2).strip()
            # If current section had questions or content, save it
            if current_section.questions:
                sections.append(current_section)
            current_section = ExtractedSection(
                title=f"{sec_num}. {sec_name}",
                order_index=order_counter,
            )
            order_counter += 1
            current_question = None
            continue

        # Check for individual question or subsection
        q_match = question_re.match(line_str)
        if q_match:
            q_num, q_body = q_match.group(1), q_match.group(2).strip()

            # Check if this is just a subsection header (e.g. "3.1 Murabaha Financing", "3.2 Ijarah")
            # Subsection headers are short (< 6 words), don't end in question marks, and lack action verbs
            is_subsection = (
                len(q_body.split()) <= 5
                and not q_body.endswith("?")
                and not any(
                    q_body.lower().startswith(v)
                    for v in (
                        "describe",
                        "provide",
                        "state",
                        "does",
                        "how",
                        "what",
                        "list",
                        "confirm",
                        "explain",
                        "detail",
                        "submit",
                        "is ",
                        "are ",
                        "can ",
                    )
                )
                and not ("[MANDATORY]" in q_body.upper() or "[OPTIONAL]" in q_body.upper())
            )
            if is_subsection:
                # Update current section title or context to include this subsection
                current_question = None
                continue

            # Determine mandatory flag
            mandatory = True
            if "[OPTIONAL]" in q_body.upper():
                mandatory = False
            elif "[MANDATORY]" in q_body.upper():
                mandatory = True

            # Clean mandatory/optional tags from question body
            clean_body = re.sub(
                r"\[(MANDATORY|OPTIONAL)\]", "", q_body, flags=re.IGNORECASE
            ).strip()

            # Determine kind
            kind = QuestionKind.narrative
            if (
                "compliance matrix" in current_section.title.lower()
                or "compliance matrix" in clean_body.lower()
            ):
                kind = QuestionKind.compliance_item

            # Determine category, owner, and status
            cat, owner, status = classify_question(clean_body, current_section.title)

            current_question = ExtractedQuestion(
                number=q_num,
                text=clean_body,
                mandatory=mandatory,
                kind=kind,
                category=cat,
                status=status,
                owner=owner,
                section_title=current_section.title,
            )
            current_section.questions.append(current_question)
            continue

        # Continuation of multi-line question text
        if current_question and not line_str.startswith("#") and not line_str.startswith("=="):
            # If line is not a subsection header like "3.1 Murabaha Financing"
            if not re.match(r"^\d+\.\d+\s+[A-Za-z]", line_str):
                current_question.text += f" {line_str}"

    if current_section.questions:
        sections.append(current_section)

    return sections
