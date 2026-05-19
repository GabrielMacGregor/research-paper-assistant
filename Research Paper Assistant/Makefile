.PHONY: install download ingest embed pipeline test lint format check

install:
	pip install -r requirements.txt

download:
	python scripts/download_papers.py

ingest:
	python src/ingestion.py

embed:
	python src/embeddings.py

pipeline: download ingest embed
	@echo "Pipeline complete — ChromaDB is ready."

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/ scripts/

format:
	ruff format src/ tests/ scripts/

check: lint test
	@echo "All checks passed."
