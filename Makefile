.PHONY: install run-backend run-frontend test lint ingest clean

install:
	python -m venv .venv
	.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
	.venv\Scripts\python.exe -m pip install -e ".[dev]"

run-backend:
	.venv\Scripts\uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	.venv\Scripts\streamlit run frontend\streamlit_app.py

test:
	.venv\Scripts\pytest -v

lint:
	.venv\Scripts\ruff check .

ingest:
	.venv\Scripts\python scripts\ingest_kb.py

clean:
	rmdir /s /q .venv __pycache__ .pytest_cache .ruff_cache chroma_db test_chroma_db rfp_agent.db 2>nul
