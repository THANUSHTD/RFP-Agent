"""
backend/app/services/document_parser.py — Document text extractor and chunker.

Supports:
- Markdown (.md) and plain text (.txt)
- Microsoft Word (.docx)
- Adobe PDF (.pdf)

Provides:
- Frontmatter metadata extraction (for structured KB docs)
- Hierarchical semantic chunking preserving document headers
"""
import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    document_name: str
    source_type: str  # product_doc | sow | past_response
    product: str | None
    product_version: str | None
    doc_date: str | None
    title: str
    text: str
    chunk_index: int


def extract_frontmatter(raw_text: str) -> tuple[dict[str, Any], str]:
    """Extract YAML-like frontmatter between leading '---' markers if present.

    Returns:
        (metadata_dict, body_text)
    """
    metadata: dict[str, Any] = {}
    body = raw_text

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw_text, re.DOTALL)
    if match:
        yaml_content, body = match.group(1), match.group(2)
        for line in yaml_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                metadata[k] = v

    return metadata, body.strip()


def parse_markdown_or_txt(file_path: str) -> tuple[dict[str, Any], str]:
    """Read a markdown or plain text file."""
    with open(file_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    return extract_frontmatter(content)


def parse_docx(file_path: str) -> tuple[dict[str, Any], str]:
    """Extract text from a DOCX file using python-docx."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)
    return extract_frontmatter(full_text)


def parse_pdf(file_path: str) -> tuple[dict[str, Any], str]:
    """Extract text from a PDF file using pymupdf (fitz)."""
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    pages_text = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages_text.append(text.strip())
    doc.close()

    full_text = "\n\n".join(pages_text)
    return extract_frontmatter(full_text)


def extract_text_from_file(file_path: str) -> tuple[dict[str, Any], str]:
    """Dispatch file reading based on extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".md", ".markdown", ".txt"):
        return parse_markdown_or_txt(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    else:
        # Fallback to plain text read
        return parse_markdown_or_txt(file_path)


def chunk_text(
    *,
    document_name: str,
    source_type: str,
    text: str,
    product: str | None = None,
    product_version: str | None = None,
    doc_date: str | None = None,
    target_chunk_size: int = 1000,
    overlap: int = 150,
) -> list[DocumentChunk]:
    """Split document text into semantic chunks with overlapping boundaries.

    Uses markdown header boundaries (# / ## / ###) and paragraphs.
    """
    if not text.strip():
        return []

    # Split into sections based on markdown headers or double newlines
    header_pattern = re.compile(r"(^(?:#{1,4}\s+.+|[A-Z0-9\.\-\s]{3,}:)$)", re.MULTILINE)
    
    sections = []
    current_title = os.path.splitext(document_name)[0]
    
    lines = text.splitlines()
    current_lines: list[str] = []

    for line in lines:
        if header_pattern.match(line):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
                current_lines = []
            current_title = line.strip("# :")
        current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    chunks: list[DocumentChunk] = []
    chunk_idx = 0

    for section_title, section_text in sections:
        if not section_text:
            continue

        # If section is small enough, it becomes one chunk
        if len(section_text) <= target_chunk_size:
            chunk_id = f"{document_name}#c{chunk_idx}"
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    document_name=document_name,
                    source_type=source_type,
                    product=product,
                    product_version=product_version,
                    doc_date=doc_date,
                    title=section_title,
                    text=f"### {section_title}\n{section_text}",
                    chunk_index=chunk_idx,
                )
            )
            chunk_idx += 1
        else:
            # Sub-chunk by paragraphs
            paragraphs = section_text.split("\n\n")
            curr_buf = ""
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                if len(curr_buf) + len(p) > target_chunk_size and curr_buf:
                    chunk_id = f"{document_name}#c{chunk_idx}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            document_name=document_name,
                            source_type=source_type,
                            product=product,
                            product_version=product_version,
                            doc_date=doc_date,
                            title=section_title,
                            text=f"### {section_title}\n{curr_buf.strip()}",
                            chunk_index=chunk_idx,
                        )
                    )
                    chunk_idx += 1
                    # Keep overlap from end of previous buffer
                    curr_buf = curr_buf[-overlap:] + "\n" + p
                else:
                    curr_buf = (curr_buf + "\n\n" + p).strip()

            if curr_buf.strip():
                chunk_id = f"{document_name}#c{chunk_idx}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_name=document_name,
                        source_type=source_type,
                        product=product,
                        product_version=product_version,
                        doc_date=doc_date,
                        title=section_title,
                        text=f"### {section_title}\n{curr_buf.strip()}",
                        chunk_index=chunk_idx,
                    )
                )
                chunk_idx += 1

    return chunks
