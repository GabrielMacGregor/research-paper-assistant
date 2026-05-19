# Phase 5 Plan — Infrastructure & Deployment

> Phase: 5 | Status: ready | Created: 2026-05-19 | Depends on: Phase 4

## Goal

Docker image, GitHub Actions CI/CD, and live Hugging Face Spaces demo. Paper browser + RAGAS dashboard work in the demo; chat shows a friendly message (Ollama unavailable on HF Spaces free tier).

## Pre-conditions

- Phase 4 complete: `streamlit run app/main.py` works locally
- HF Space created manually at huggingface.co/new-space (SDK: Docker, name: `research-paper-assistant`)
- `HF_TOKEN` added to GitHub repo secrets (Settings → Secrets → Actions)

## Architecture

```
Dockerfile                    ← python:3.11-slim, CPU torch, port 7860, uid 1000
.dockerignore                 ← exclude .git, PDFs, chroma_db (~2GB savings)
docker-compose.yml            ← local dev convenience
requirements-ci.txt           ← lightweight subset for GitHub Actions (no torch)
.github/workflows/ci.yml      ← lint + test on push/PR (uses requirements-ci.txt)
.github/workflows/deploy.yml  ← push to HF Spaces on main merge (needs ci to pass)
app.py                        ← root-level entrypoint (HF Spaces Streamlit SDK fallback)
evaluation/results/           ← ragas_scores.json committed (demo scores for HF Spaces)
```

---

## Execution Waves

---

### Wave 1 — Docker files (run in parallel)

#### Task 1.1 — Create `Dockerfile`

```dockerfile
FROM python:3.11-slim

# Install CPU-only torch first to prevent pip from pulling GPU variant
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Non-root user (HF Spaces requires uid 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    EMBEDDING_DEVICE=cpu \
    OLLAMA_BASE_URL=http://localhost:11434

WORKDIR /home/user/app

# Install Python dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user:user . .

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/_stcore/health')"

CMD ["streamlit", "run", "app/main.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

#### Task 1.2 — Create `.dockerignore`

```
.git
.github
.planning
.venv
venv
get-shit-done
data/papers/
data/chroma_db/
__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov
.env
*.env
```

Note: `evaluation/results/ragas_scores.json` is intentionally NOT excluded — the demo scores file is included in the image.

#### Task 1.3 — Create `docker-compose.yml`

```yaml
services:
  app:
    build: .
    ports:
      - "8501:7860"
    environment:
      - EMBEDDING_DEVICE=cpu
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    volumes:
      - ./data/chroma_db:/home/user/app/data/chroma_db
      - ./evaluation/results:/home/user/app/evaluation/results
```

`host.docker.internal` lets the container reach Ollama running on the host (Mac/Windows). For Linux, use `172.17.0.1` or `--add-host=host.docker.internal:host-gateway`.

---

### Wave 2 — CI requirements file

#### Task 2.1 — Create `requirements-ci.txt`

Lightweight subset — heavy ML packages (`torch`, `chromadb`, `sentence-transformers`, `langchain-huggingface`, `langchain-ollama`) are mocked in `tests/conftest.py` and not needed for tests to pass.

```
# CI dependencies — heavy packages mocked in tests/conftest.py
pydantic-settings==2.8.1
python-dotenv==1.1.0
pymupdf==1.27.2
langchain-core
langchain-text-splitters
ragas==0.2.15
pandas
numpy
streamlit==1.45.1
pytest==8.3.5
pytest-cov==6.1.0
ruff==0.11.10
```

---

### Wave 3 — GitHub Actions workflows (run in parallel)

#### Task 3.1 — Create `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: requirements-ci.txt

      - name: Install dependencies
        run: pip install -r requirements-ci.txt

      - name: Lint
        run: ruff check src/ tests/ scripts/ evaluation/ app/

      - name: Test
        run: pytest tests/ -v --tb=short
```

#### Task 3.2 — Create `.github/workflows/deploy.yml`

```yaml
name: Deploy to HF Spaces

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    needs: []
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          lfs: true

      - name: Push to Hugging Face Spaces
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git config user.email "action@github.com"
          git config user.name "GitHub Actions"
          git remote add space https://GabrielMacGregor:$HF_TOKEN@huggingface.co/spaces/GabrielMacGregor/research-paper-assistant
          git push space main --force
```

**Pre-requisite**: `HF_TOKEN` must be added to GitHub repo → Settings → Secrets and variables → Actions → New repository secret. Get the token from https://huggingface.co/settings/tokens (write access).

---

### Wave 4 — Demo data + fixes (run in parallel)

#### Task 4.1 — Commit demo `evaluation/results/ragas_scores.json`

Remove from `.gitignore` and create a placeholder scores file. This ensures the RAGAS dashboard shows in the HF Spaces demo even before the user runs `make eval`.

Update `.gitignore`: remove the line `evaluation/results/ragas_scores.json`.

Create `evaluation/results/ragas_scores.json`:

```json
{
  "aggregate": {
    "faithfulness": 0.0,
    "answer_relevancy": 0.0,
    "context_precision": 0.0,
    "n_questions": 0
  },
  "per_question": [],
  "_note": "Run `make eval` on a machine with Ollama + ChromaDB to populate real scores."
}
```

Using zeroes with a note makes it clear these are placeholders, not real scores.

#### Task 4.2 — Fix `pydantic` version constraint in `requirements.txt`

`pydantic>=2.0,<2.13` fails with pydantic 2.13+ installed (which ragas pulls in). Remove the upper bound:

Change:
```
pydantic>=2.0,<2.13
```
To:
```
pydantic>=2.0
```

---

### Wave 5 — App entrypoint + README frontmatter

#### Task 5.1 — Create `app.py` (root-level HF Spaces entrypoint)

```python
"""Root-level entrypoint for Hugging Face Spaces Streamlit SDK compatibility."""

from app.main import main

main()
```

This lets the repo work as both a Docker Space (uses `Dockerfile`) and a Streamlit SDK Space (uses `app.py`) if needed.

#### Task 5.2 — Update `README.md` — add HF Spaces frontmatter and badges

The HF Spaces frontmatter **must be the very first lines** of `README.md`.

Prepend to `README.md`:
```markdown
---
title: Research Paper Assistant
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

```

Also add stack badges and architecture diagram after the title. Full updated README.md:

```markdown
---
title: Research Paper Assistant
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Research Paper Assistant

[![CI](https://github.com/GabrielMacGregor/research-paper-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/GabrielMacGregor/research-paper-assistant/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.45-red)
![License](https://img.shields.io/badge/license-MIT-green)

A production-quality RAG (Retrieval-Augmented Generation) system for querying 25 landmark AI/ML papers. Fully local — zero API cost — with quantitative RAGAS evaluation.

## Stack

| Layer | Technology |
|---|---|
| LLM | Ollama — `mistral:7b` (local, 4GB VRAM) |
| Embeddings | `BAAI/bge-small-en-v1.5` via HuggingFace |
| Vector store | ChromaDB (local persistent) |
| Retrieval | Semantic search + MMR (Maximal Marginal Relevance) |
| Evaluation | RAGAS 0.2.x — Faithfulness, Answer Relevancy, Context Precision |
| Framework | LangChain, PyMuPDF, pydantic-settings |

## Architecture

```
PDFs (arXiv)
    └── PyMuPDF parsing
            └── LangChain chunking (512 tokens, 50 overlap)
                    └── BAAI/bge-small-en-v1.5 embeddings
                            └── ChromaDB (local persist)

User question
    └── Embed query
            └── Semantic search + MMR reranking (top-5)
                    └── LangChain prompt template
                            └── Ollama mistral:7b (local)
                                    └── Cited answer + RAGAS scores
```

## RAGAS Evaluation

| Metric | Score | Threshold | Status |
|---|---|---|---|
| Faithfulness | — | ≥ 0.85 | Run `make eval` |
| Answer Relevancy | — | ≥ 0.80 | Run `make eval` |
| Context Precision | — | ≥ 0.75 | Run `make eval` |

_Run `make eval` on a machine with Ollama + populated ChromaDB to fill in real scores._

## Corpus — 25 Papers

Attention Is All You Need · BERT · GPT-3 · RAG · DPR · ColBERT · FAISS · LoRA · InstructGPT · Constitutional AI · Chain-of-Thought · ReAct · Self-Consistency · Mistral 7B · CLIP · LLaMA · Stable Diffusion · DALL-E · Vision Transformer · Neural Turing Machine · Memory Networks · World Models · Decision Transformer · Diffusion Models · AlphaCode

## Quick Start

**Requirements:** Python 3.11+, Ollama installed with `mistral:7b` pulled, NVIDIA GPU (4GB+ VRAM recommended).

```bash
# Install dependencies
pip install -r requirements.txt

# Pull the LLM (one-time)
ollama pull mistral:7b

# Build the knowledge base (download PDFs → parse → embed → store)
make pipeline

# Ask a question
make ask QUERY="What is the attention mechanism in Transformers?"

# Launch the UI
make ui
```

## Docker

```bash
# Build
docker build -t research-paper-assistant .

# Run (connects to Ollama on host)
docker run -p 8501:7860 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  research-paper-assistant
```

## Running RAGAS Evaluation

```bash
make eval-sample   # 5 questions (~5-10 min)
make eval          # 25 questions (~15-45 min)
```

## Project Structure

```
config/             pydantic-settings configuration (.env support)
data/
  papers_metadata.json   25 papers with arXiv IDs, titles, authors, years
  papers/                downloaded PDFs (gitignored)
  chroma_db/             vector store (gitignored)
evaluation/
  test_questions.json    25 Q&A pairs with reference answers (5 categories)
  eval.py                RAGAS evaluation pipeline
  results/               score outputs
app/
  main.py                Streamlit entrypoint
  components/            chat, sources, paper_browser, eval_dashboard
src/
  ingestion.py           PDF parsing + chunking (PyMuPDF)
  embeddings.py          HuggingFace embeddings → ChromaDB
  retriever.py           semantic search + MMR
  pipeline.py            full RAG pipeline: query → answer + citations
  llm.py                 Ollama LLM wrapper
  prompts.py             system prompt template
tests/                   44 unit tests (all mocked — no GPU needed)
```

## Implementation Status

| Phase | Description | Status |
|---|---|---|
| 1 — Data Pipeline | Download → parse → embed → ChromaDB | Complete |
| 2 — RAG Pipeline | Retrieve → prompt → Ollama → cited response | Complete |
| 3 — RAGAS Evaluation | 25 Q&A pairs + local LLM judge + score report | Complete |
| 4 — Streamlit UI | Streaming chat + paper browser + RAGAS dashboard | Complete |
| 5 — Infrastructure | Docker + GitHub Actions CI/CD + HF Spaces deploy | Complete |

## Configuration

Copy `.env.example` to `.env` to override defaults:

```env
OLLAMA_MODEL=mistral:7b
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DEVICE=cuda
TOP_K=5
```
```

---

### Wave 6 — Makefile updates

#### Task 6.1 — Add Docker targets to `Makefile`

Update `.PHONY` and add targets:

```makefile
.PHONY: install download ingest embed pipeline ask eval eval-sample ui docker-build docker-run test lint format check

docker-build:
	docker build -t research-paper-assistant .

docker-run:
	docker run -p 8501:7860 \
		-e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
		research-paper-assistant
```

---

## Verification Steps

```bash
# 1. Docker build
docker build -t research-paper-assistant .

# 2. Docker run
docker run -p 8501:7860 research-paper-assistant
# → open http://localhost:8501
# → paper browser should load, RAGAS scores show 0.0 (placeholder)

# 3. Tests still pass
pytest tests/ -v

# 4. Lint
ruff check src/ tests/ scripts/ evaluation/ app/
```

## UAT Checklist

- [ ] `docker build -t research-paper-assistant .` exits 0
- [ ] `docker run -p 8501:7860 research-paper-assistant` → Streamlit loads on http://localhost:8501
- [ ] Paper browser shows 25 papers in running container
- [ ] RAGAS dashboard shows placeholder scores (all 0.0 with note)
- [ ] Chat shows Ollama error gracefully (no crash)
- [ ] `pytest tests/ -v` — all 44 tests pass
- [ ] `ruff check` — lint clean
- [ ] CI passes on GitHub (push to main triggers ci.yml)
- [ ] HF Spaces URL loads after deploy (paper browser + RAGAS panel visible)

## Manual Pre-requisites (one-time, done by user)

1. Create HF Space at https://huggingface.co/new-space
   - Owner: GabrielMacGregor
   - Space name: research-paper-assistant
   - SDK: **Docker**
   - Visibility: Public

2. Get HF write token at https://huggingface.co/settings/tokens

3. Add `HF_TOKEN` secret to GitHub:
   - Repo → Settings → Secrets and variables → Actions → New repository secret

## Phase Complete Criteria

Docker builds + CI passes + HF Spaces URL accessible with paper browser visible.
