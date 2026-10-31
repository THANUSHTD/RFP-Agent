"""
backend/app/services/redaction.py — PII and confidential information redactor.

Strict requirement from brief:
- SOWs and past RFP responses must be redacted at ingestion time.
- Redact client names, pricing, email addresses, phone numbers, and secrets.
- Redaction happens BEFORE storage in Chroma / SQLite; original text is never persisted.
"""

import re

# Standard replacement tokens
TOKEN_CLIENT = "[REDACTED_CLIENT]"
TOKEN_PRICING = "[REDACTED_PRICING]"
TOKEN_EMAIL = "[REDACTED_EMAIL]"
TOKEN_PHONE = "[REDACTED_PHONE]"
TOKEN_SECRET = "[REDACTED_SECRET]"

# Explicit known client entities in synthetic past SOWs / RFPs
KNOWN_CLIENTS = [
    "Bank Al-Noor",
    "Bank Al Noor",
    "Al-Noor Bank",
    "Gulf Credit Corporation",
    "Gulf Credit Corp",
    "Gulf Credit",
    "Al-Hilal Bank",
    "Al Hilal Bank",
    "Riyadh Finance Company",
    "Riyadh Finance",
    "Noor Islamic Bank",
    "Al-Baraka Bank",
]

# Regex patterns
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

# Phone numbers (international, hyphenated, bracketed, handles 1-4 digit area codes)
RE_PHONE = re.compile(r"(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{1,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b")


# Pricing / Currency amounts (USD, AED, SAR, EUR, GBP, $, etc.)
RE_PRICING = re.compile(
    r"(?:\$|USD|AED|SAR|EUR|GBP)\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:k|K|M|million|USD|AED|SAR))?"
    r"|\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|AED|SAR|EUR|GBP)(?:\s*/\s*(?:hr|hour|day|user|month|year))?"
    r"|\$\d+(?:\.\d{2})?\s*/\s*(?:hr|hour|day|user)",
    re.IGNORECASE,
)

# Secrets / credentials
RE_SECRET = re.compile(
    r"(?:api[_-]?key|secret|password|bearer|token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{8,}['\"]?",
    re.IGNORECASE,
)

# Pattern for generic Client / Bank names
RE_BANK_PATTERN = re.compile(
    r"\b(?:Bank\s+[A-Z][a-zA-Z\-]+|[A-Z][a-zA-Z\-]+\s+(?:Islamic\s+)?Bank)\b"
)


def redact_text(text: str) -> tuple[str, bool]:
    """Redact sensitive PII and commercial secrets from text.

    Args:
        text: Raw source text.

    Returns:
        (redacted_text, was_redacted): Tuple of modified string and bool flag.
    """
    if not text:
        return text, False

    modified = text

    # 1. Redact known client names
    for client in KNOWN_CLIENTS:
        # Case insensitive word replacement
        pattern = re.compile(re.escape(client), re.IGNORECASE)
        modified = pattern.sub(TOKEN_CLIENT, modified)

    # 2. Redact generic Bank entities (e.g. "Al-Amana Bank")
    modified = RE_BANK_PATTERN.sub(TOKEN_CLIENT, modified)

    # 3. Redact pricing & fees
    modified = RE_PRICING.sub(TOKEN_PRICING, modified)

    # 4. Redact emails
    modified = RE_EMAIL.sub(TOKEN_EMAIL, modified)

    # 5. Redact phone numbers (exclude standard 4-digit years like 2023 or semver like 3.0.0)
    def _phone_sub(m: re.Match) -> str:
        s = m.group(0).strip()
        # Avoid redacting pure 4-digit year like 2024
        if len(s) == 4 and s.isdigit() and 1900 <= int(s) <= 2100:
            return s
        return TOKEN_PHONE

    modified = RE_PHONE.sub(_phone_sub, modified)

    # 6. Redact secrets
    modified = RE_SECRET.sub(TOKEN_SECRET, modified)

    was_redacted = modified != text
    return modified, was_redacted
