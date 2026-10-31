"""
conftest.py — Shared pytest fixtures for the RFP Agent test suite.
"""
import os
import pytest

@pytest.fixture(autouse=True)
def patch_settings_for_tests(monkeypatch):
    """Point all tests at an in-memory SQLite DB and dummy API key."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite://")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("CHROMA_DIR", "./test_chroma_db")
    # Clear LRU cache so patched env is picked up
    from backend.app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
