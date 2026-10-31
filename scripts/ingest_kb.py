"""
scripts/ingest_kb.py — CLI utility to run Knowledge Base ingestion.

Usage:
    python scripts/ingest_kb.py [--kb-dir data/kb_sample]
"""

import argparse
import asyncio
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.db import AsyncSessionLocal, init_db
from backend.app.services.ingestion import run_kb_ingestion


async def main():
    parser = argparse.ArgumentParser(description="Ingest Knowledge Base documents.")
    parser.add_argument(
        "--kb-dir",
        default="data/kb_sample",
        help="Path to folder containing knowledge documents (default: data/kb_sample)",
    )
    args = parser.parse_args()

    print("[*] Initializing database schemas...")
    await init_db()

    kb_dir = os.path.abspath(args.kb_dir)
    print(f"[*] Starting ingestion from: {kb_dir}")

    async with AsyncSessionLocal() as session:
        result = await run_kb_ingestion(kb_dir, session)

    print("\n[+] Ingestion Complete!")
    print(f"    Total files processed: {result['processed']}")
    print(f"    Total chunks created:   {result['total_chunks']}")
    print("-" * 60)
    for f in result.get("files", []):
        redacted_badge = " [REDACTED]" if f.get("redacted") else ""
        print(f"  • {f['filename']} ({f['source_type']}){redacted_badge} -> {f['chunks']} chunks")
    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
