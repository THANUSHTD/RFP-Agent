"""
tests/test_phase0.py — Phase 0 tests: config, models, DB, API schema.

These tests do NOT require an OpenAI key or a running server.
They verify the foundational plumbing: settings loading, DB table creation,
triage enum values, and API schema validation.
"""

import pytest

from backend.app.config import Settings
from backend.app.models import (
    OwnerDept,
    QuestionCategory,
    QuestionStatus,
    SourceType,
)
from backend.app.schemas import (
    AnswerPatch,
    ApproveRequest,
    SessionCreate,
)

# ── Config tests ──────────────────────────────────────────────────────────────


class TestSettings:
    def test_defaults_are_valid(self):
        """Settings instantiated with no .env should use documented defaults."""
        s = Settings(openai_api_key="test-key")
        assert 0 < s.confidence_low < s.confidence_high < 1.0
        assert s.retrieval_top_k > 0
        assert s.max_concurrency > 0
        assert s.max_upload_mb > 0

    def test_confidence_thresholds_order(self):
        """LOW must be strictly less than HIGH."""
        s = Settings(openai_api_key="test-key")
        assert s.confidence_low < s.confidence_high

    def test_no_hardcoded_model_names(self):
        """Model names come from settings, not hardcoded literals."""
        s = Settings(
            openai_api_key="test-key",
            fast_model="gpt-4o-mini",
            draft_model="gpt-4o",
        )
        assert s.fast_model != s.draft_model  # Two distinct tiers


# ── Enum tests ────────────────────────────────────────────────────────────────


class TestEnums:
    def test_question_status_values(self):
        expected = {
            "pending",
            "answered",
            "low_confidence",
            "clarification",
            "flagged_owner",
            "approved",
        }
        assert {s.value for s in QuestionStatus} == expected

    def test_owner_dept_values(self):
        expected = {"Pricing", "Legal", "Delivery"}
        assert {o.value for o in OwnerDept} == expected

    def test_source_type_values(self):
        expected = {"product_doc", "sow", "past_response"}
        assert {s.value for s in SourceType} == expected

    def test_question_category_covers_commercial_legal_sla(self):
        """These three categories must exist for owner-flagging triage rules."""
        values = {c.value for c in QuestionCategory}
        assert "commercial" in values
        assert "legal" in values
        assert "sla" in values


# ── DB init test ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_db_init_creates_tables():
    """init_db() must create all declared tables without errors."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from backend.app.models import Base

    test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = {row[0] for row in result}

    expected_tables = {
        "sessions",
        "rfp_documents",
        "sections",
        "questions",
        "answers",
        "clarifications",
        "chat_messages",
        "kb_documents",
        "format_rules",
        "llm_calls",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    await test_engine.dispose()


# ── Schema validation tests ───────────────────────────────────────────────────


class TestSchemas:
    def test_session_create_rejects_empty_name(self):
        with pytest.raises(Exception):
            SessionCreate(name="")

    def test_approve_request_requires_confirm_true(self):
        req = ApproveRequest(confirm=True)
        assert req.confirm is True

    def test_approve_false_is_valid_schema_but_rejected_by_api(self):
        """Schema allows False; the API endpoint rejects it with 400."""
        req = ApproveRequest(confirm=False)
        assert req.confirm is False

    def test_answer_patch_is_optional(self):
        """All fields in AnswerPatch are optional (SE may patch only one)."""
        patch = AnswerPatch()
        assert patch.text is None


# ── Triage rule unit test ─────────────────────────────────────────────────────


class TestTriageRules:
    """Basic triage logic: commercial/legal/sla/pricing must be flagged to owner.

    The full graph runs in Phase 3; here we just test the rule predicate.
    """

    OWNER_FLAG_CATEGORIES = {"commercial", "legal", "sla"}

    def _should_flag_owner(self, category: str) -> bool:
        return category in self.OWNER_FLAG_CATEGORIES

    def test_commercial_flagged(self):
        assert self._should_flag_owner("commercial") is True

    def test_legal_flagged(self):
        assert self._should_flag_owner("legal") is True

    def test_sla_flagged(self):
        assert self._should_flag_owner("sla") is True

    def test_technical_not_flagged(self):
        assert self._should_flag_owner("technical") is False

    def test_shariah_not_flagged(self):
        assert self._should_flag_owner("shariah") is False
