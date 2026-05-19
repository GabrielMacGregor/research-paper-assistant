.PHONY: install download ingest embed pipeline ask eval eval-sample test lint format check

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

ask:
	@if [ -z "$(QUERY)" ]; then echo "Usage: make ask QUERY='your question here'"; exit 1; fi
	python src/pipeline.py --query "$(QUERY)"

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/ scripts/

format:
	ruff format src/ tests/ scripts/

eval:
	python evaluation/eval.py

eval-sample:
	python evaluation/eval.py --sample 5

check: lint test
	@echo "All checks passed."
