# AI Disclosure

This document discloses the use of AI tools and models in the development and
operation of the RFP Agent.

## AI Models Used at Runtime

| Model | Purpose | Configured Via |
|---|---|---|
| `FAST_MODEL` (default: gpt-4o-mini) | Triage, parsing, extraction, classification, verification, redaction | `.env` |
| `DRAFT_MODEL` (default: gpt-4o) | Answer drafting, rewrites, chat agent responses | `.env` |
| `EMBEDDING_MODEL` (default: text-embedding-3-small) | Vector embeddings for semantic search | `.env` |

All LLM calls are logged in the `llm_calls` table (model, token counts, latency, purpose).

## AI Tools Used in Development

| Tool | Purpose |
|---|---|
| Google Antigravity (Claude/Gemini) | Code generation, architecture design, documentation |
| OpenAI API | Runtime LLM and embedding calls |

## Data Handling

- All documents processed by the LLM are wrapped in clear delimiters and marked as untrusted data.
- No real customer, prospect, or personal data is used. All sample content is labelled **SAMPLE**.
- Past RFP responses and SOWs are redacted (customer names, emails, phone numbers replaced with placeholders) before being stored or sent to the LLM.
- API keys are never logged, printed, or included in any output.

## Human Oversight

- Every drafted answer requires explicit SE approval before it is treated as final.
- The agent never auto-approves answers.
- Pricing, SLA, and legal questions are never auto-answered; they are flagged to named owners.
