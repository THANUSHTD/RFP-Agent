"""
llm.py — Thin wrapper around the OpenAI API.

Provides:
  fast(messages, response_format)  — uses FAST_MODEL
  draft(messages, response_format) — uses DRAFT_MODEL
  embed(texts)                     — uses EMBEDDING_MODEL

Features:
  - Retries with exponential backoff (tenacity)
  - Logs every call to the llm_calls table (model, tokens, latency, purpose)
  - Structured output via response_format parameter (Pydantic schema or None)
  - Never logs full message content or API keys
"""
import asyncio
import logging
import time
from typing import Any, TypeVar

from openai import AsyncOpenAI, RateLimitError, APIError
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton client — created once, reused for the application lifetime.
_client = AsyncOpenAI(api_key=settings.openai_api_key)

T = TypeVar("T", bound=BaseModel)


# ── Retry decorator for transient OpenAI errors ───────────────────────────────

_retry = retry(
    retry=retry_if_exception_type((RateLimitError, APIError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)


# ── Internal logging helper ───────────────────────────────────────────────────

async def _log_call(
    *,
    model: str,
    purpose: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    session_id: int | None = None,
) -> None:
    """Persist an LLM call record.  Imports db lazily to avoid circular deps."""
    try:
        from backend.app.db import AsyncSessionLocal
        from backend.app.models import LLMCall

        async with AsyncSessionLocal() as db:
            db.add(
                LLMCall(
                    model=model,
                    purpose=purpose,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    session_id=session_id,
                )
            )
            await db.commit()
    except Exception as exc:  # Never crash main flow due to logging
        logger.warning("Failed to log LLM call: %s", exc)


# ── Core call function ────────────────────────────────────────────────────────

@_retry
async def _call(
    *,
    model: str,
    messages: list[dict[str, str]],
    purpose: str,
    response_format: type[BaseModel] | None = None,
    session_id: int | None = None,
    temperature: float = 0.2,
) -> Any:
    """Make one OpenAI chat completion call.

    Args:
        model: Model name from settings (never a hardcoded string).
        messages: OpenAI message list.
        purpose: Short label for audit logging (e.g. "draft_answer").
        response_format: Pydantic schema for structured output, or None.
        session_id: Optional session ID for audit correlation.
        temperature: Sampling temperature; default low for consistency.

    Returns:
        Parsed Pydantic object if response_format is given, else plain string.
    """
    start = time.monotonic()

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if response_format is not None:
        # Use OpenAI structured outputs (JSON schema mode)
        kwargs["response_format"] = response_format

    if response_format is not None:
        response = await _client.beta.chat.completions.parse(**kwargs)
        result = response.choices[0].message.parsed
    else:
        response = await _client.chat.completions.create(**kwargs)
        result = response.choices[0].message.content or ""

    latency_ms = int((time.monotonic() - start) * 1000)
    usage = response.usage

    # Log asynchronously — do not block the caller
    asyncio.create_task(
        _log_call(
            model=model,
            purpose=purpose,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
            session_id=session_id,
        )
    )

    logger.info(
        "LLM call | model=%s purpose=%s tokens=%s latency_ms=%d",
        model,
        purpose,
        usage.total_tokens if usage else "?",
        latency_ms,
    )

    return result


# ── Public helpers ────────────────────────────────────────────────────────────

async def fast(
    messages: list[dict[str, str]],
    purpose: str,
    response_format: type[BaseModel] | None = None,
    session_id: int | None = None,
) -> Any:
    """Call the FAST_MODEL (triage, parsing, extraction, verification)."""
    return await _call(
        model=settings.fast_model,
        messages=messages,
        purpose=purpose,
        response_format=response_format,
        session_id=session_id,
    )


async def draft(
    messages: list[dict[str, str]],
    purpose: str,
    response_format: type[BaseModel] | None = None,
    session_id: int | None = None,
) -> Any:
    """Call the DRAFT_MODEL (answer drafting, rewrites, chat agent)."""
    return await _call(
        model=settings.draft_model,
        messages=messages,
        purpose=purpose,
        response_format=response_format,
        session_id=session_id,
    )


@_retry
async def embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using EMBEDDING_MODEL.

    Returns a list of float vectors, one per input text.
    """
    if not texts:
        return []

    response = await _client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    # Sort by index to guarantee ordering matches input
    items = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in items]
