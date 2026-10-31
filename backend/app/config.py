"""
config.py — Application settings loaded from environment variables.

Uses pydantic-settings so every field is typed and validated at startup.
Never hardcode model names or thresholds here; they all come from .env.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configurable values for the RFP Agent.

    Fields map 1-to-1 to the env vars documented in .env.example.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    fast_model: str = "gpt-4o-mini"
    draft_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # ── Product / Staleness ───────────────────────────────────────────────
    current_product_version: str = "3.0.0"
    stale_after_months: int = 18

    # ── Retrieval ─────────────────────────────────────────────────────────
    confidence_high: float = 0.75
    confidence_low: float = 0.45
    retrieval_top_k: int = 8

    # ── Concurrency ───────────────────────────────────────────────────────
    max_concurrency: int = 4

    # ── Storage ───────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./rfp_agent.db"
    chroma_dir: str = "./chroma_db"

    # ── Upload ────────────────────────────────────────────────────────────
    max_upload_mb: int = 50

    # ── Service URLs ──────────────────────────────────────────────────────
    backend_url: str = "http://localhost:8000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
