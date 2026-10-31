"""
conftest.py — Shared pytest fixtures for the RFP Agent test suite.
"""

import asyncio
import os
import shutil

import pytest

TEST_DB_FILE = "./test_rfp_agent.db"
TEST_CHROMA_DIR = "./test_chroma_db"


@pytest.fixture(autouse=True)
def patch_settings_for_tests(monkeypatch):
    """Point all tests at test SQLite DB and dummy API key."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_FILE}")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy")
    monkeypatch.setenv("CHROMA_DIR", TEST_CHROMA_DIR)

    from backend.app.config import get_settings

    get_settings.cache_clear()

    # Initialize tables for tests
    from backend.app.db import init_db

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(init_db())
        else:
            loop.run_until_complete(init_db())
    except RuntimeError:
        asyncio.run(init_db())

    yield

    get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    yield
    # Clean up test files after test session
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
    if os.path.exists(TEST_CHROMA_DIR):
        try:
            shutil.rmtree(TEST_CHROMA_DIR, ignore_errors=True)
        except Exception:
            pass
