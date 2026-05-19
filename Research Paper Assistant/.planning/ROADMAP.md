# Roadmap — Research Paper Assistant

> Version: 0.1.0 | Created: 2026-05-19

## Milestone: v1.0 — Production-Quality RAG Portfolio Project

**Goal**: A complete, evaluated, deployed RAG application for AI/ML research papers.
**Target**: HF Spaces public demo with RAGAS scores ≥ quality thresholds.

---

## Phase 1 — Project Setup & Data Pipeline
**Status**: pending
**Goal**: Repository structure, tooling, and all 25 papers ingested into ChromaDB.

### Deliverables
- `pyproject.toml` / `requirements.txt` with all pinned dependencies
- `data/papers/` with 25 arXiv PDFs
- `data/papers_metadata.json` with structured metadata (title, authors, year, arXiv ID)
- `scripts/download_papers.py` — automated arXiv downloader
- `src/ingestion.py` — PDF parsing with PyMuPDF + LangChain chunking
- `src/embeddings.py` — HuggingFace BAAI/bge-small-en-v1.5 + ChromaDB persistence
- `.env.example` with all required keys
- `.gitignore` (excludes `.env`, `data/chroma_db/`, PDFs)
- `Makefile` with `make ingest`, `make embed` targets

### Verification
- `python scripts/download_papers.py` downloads all 25 papers
- `python src/ingestion.py` exits 0 with no errors
- `python src/embeddings.py` populates ChromaDB — verify with chunk count log
- Unit tests: `tests/test_ingestion.py`, `tests/test_embeddings.py`

### UAT
- [ ] All 25 papers present in `data/papers/`
- [ ] ChromaDB collection contains ≥ 500 chunks total
- [ ] Each chunk has metadata: paper_id, title, authors, year, page, chunk_index
- [ ] Re-running ingestion + embeddings is idempotent (no duplicates)

---

## Phase 2 — RAG Pipeline
**Status**: pending
**Depends on**: Phase 1
**Goal**: End-to-end query → answer pipeline with citations.

### Deliverables
- `src/retriever.py` — semantic search + MMR, configurable K
- `src/llm.py` — `OllamaLLM` wrapper via `langchain-ollama`, model name from `OLLAMA_MODEL` env
- `src/pipeline.py` — orchestrates retriever + prompt builder + LLM + response formatter
- `src/prompts.py` — prompt templates with citation instructions
- `config/settings.py` — pydantic settings loaded from env (includes `OLLAMA_BASE_URL`, `OLLAMA_MODEL`)

### Verification
- `python src/pipeline.py --query "What is the attention mechanism?"` returns answer with sources
- Unit tests: `tests/test_retriever.py`, `tests/test_pipeline.py`
- Integration test: full pipeline with mocked LLM

### UAT
- [ ] Query returns `answer`, `sources` (≥1 citation), `context_chunks`
- [ ] Ollama is running locally (`ollama serve`) with `mistral:7b` pulled
- [ ] `python src/pipeline.py --query "..."` connects to Ollama and returns answer
- [ ] Switching model via `OLLAMA_MODEL=llama3.1:8b` works without code changes
- [ ] No relevant context → graceful "I couldn't find relevant information" response
- [ ] Response cites paper name and year

---

## Phase 3 — RAGAS Evaluation
**Status**: pending
**Depends on**: Phase 2
**Goal**: Quantitative quality measurement on a curated test set.

### Deliverables
- `evaluation/test_questions.json` — 25 question-answer-context pairs covering the corpus
- `evaluation/eval.py` — runs RAGAS metrics (faithfulness, answer_relevancy, context_precision)
- `evaluation/results/ragas_scores.json` — output scores
- `evaluation/results/ragas_report.md` — human-readable summary with per-question breakdown

### Question Set Design
- 5 questions about Transformers/Attention
- 5 questions about RAG/Retrieval
- 5 questions about Fine-tuning/LoRA
- 5 questions about Prompting techniques
- 5 cross-paper synthesis questions

### Verification
- `python evaluation/eval.py` completes without error
- Output JSON contains all three metric keys
- Unit test: `tests/test_evaluation.py` with mocked RAGAS

### UAT
- [ ] `ragas_scores.json` contains `faithfulness`, `answer_relevancy`, `context_precision`
- [ ] `faithfulness` ≥ 0.85
- [ ] `answer_relevancy` ≥ 0.80
- [ ] `context_precision` ≥ 0.75
- [ ] Per-question breakdown available in `ragas_report.md`

---

## Phase 4 — Streamlit Interface
**Status**: pending
**Depends on**: Phase 2, Phase 3
**Goal**: Interactive chat UI with citations, paper browser, and RAGAS dashboard.

### Deliverables
- `app/main.py` — Streamlit app entrypoint
- `app/components/chat.py` — chat interface with session history
- `app/components/sources.py` — source citations display component
- `app/components/paper_browser.py` — indexed papers list with metadata
- `app/components/eval_dashboard.py` — RAGAS scores sidebar widget

### UI Flows
1. **Chat**: User types question → answer streams in → sources shown below
2. **Paper Browser**: Expandable list of all indexed papers with title/year/abstract
3. **Eval Dashboard**: Sidebar showing latest RAGAS scores with color-coded indicators

### Verification
- `streamlit run app/main.py` starts without error
- Manual test: 5 questions answered with citations
- Visual check: RAGAS scores appear in sidebar

### UAT
- [ ] Chat interface responds to questions
- [ ] Each response shows ≥1 source citation with paper title + year
- [ ] Conversation history persists within session
- [ ] Paper browser lists all 25 papers
- [ ] RAGAS scores visible in sidebar (loads from `evaluation/results/ragas_scores.json`)
- [ ] Ollama model selector works (dropdown lists available local models)
- [ ] Works on mobile viewport (responsive)

---

## Phase 5 — Infrastructure & Deployment
**Status**: pending
**Depends on**: Phase 4
**Goal**: Docker image, CI/CD pipeline, and live HF Spaces demo.

### Deliverables
- `Dockerfile` — multi-stage build, non-root user, health check
- `docker-compose.yml` — local dev with volume mounts
- `.github/workflows/ci.yml` — lint + tests + build check on push/PR
- `.github/workflows/deploy.yml` — deploy to HF Spaces on main merge
- `README.md` — full project documentation with:
  - Architecture diagram (ASCII or Mermaid)
  - Quick start guide
  - RAGAS scores table
  - Demo GIF / screenshot
  - Stack badges
- `app.py` — HF Spaces entrypoint (wraps Streamlit)

### CI Pipeline Steps
1. `ruff check` — linting
2. `mypy` — type checking
3. `pytest tests/` — unit + integration tests
4. `docker build` — image builds successfully

### Verification
- `docker build -t rpa .` exits 0
- `docker run -p 8501:8501 rpa` serves Streamlit
- GitHub Actions CI green on push
- HF Spaces URL accessible and functional

### UAT
- [ ] Docker image builds in ≤ 5 minutes
- [ ] Container serves app on port 8501
- [ ] CI pipeline green (lint + tests + build)
- [ ] HF Spaces deployment live and accessible
- [ ] README includes RAGAS score table with actual values
- [ ] Demo GIF shows chat + citations
- [ ] All env vars documented in `.env.example`

---

## Backlog (Post v1.0)

- Hybrid search: BM25 + semantic (reciprocal rank fusion)
- Real-time arXiv paper ingestion via API
- Per-query RAGAS evaluation shown inline in UI
- Fine-tuned embedding model on arXiv abstracts
- Pinecone / Weaviate cloud vector store option
- LangSmith tracing integration
- Multi-language paper support
- Async ingestion pipeline

---

## Phase Dependency Graph

```
Phase 1 (Data Pipeline)
    └── Phase 2 (RAG Pipeline)
            ├── Phase 3 (RAGAS Evaluation)
            └── Phase 4 (Streamlit UI)
                        └── Phase 5 (Infrastructure & Deploy)
```
