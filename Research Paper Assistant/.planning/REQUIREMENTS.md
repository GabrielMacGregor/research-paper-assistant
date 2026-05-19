# Requirements — Research Paper Assistant

> Version: 0.1.0 | Status: Approved | Date: 2026-05-19

## Scope

This document defines what the Research Paper Assistant **must do** (functional) and **how well it must do it** (non-functional) for v1.0.

---

## Functional Requirements

### FR-01 — PDF Ingestion
- **MUST** parse PDF files from `data/papers/` using PyMuPDF
- **MUST** extract text content preserving section structure
- **MUST** chunk text with configurable size (default: 512 tokens) and overlap (default: 50 tokens)
- **MUST** store metadata per chunk: paper title, authors, year, arXiv ID, section, page number
- **MUST** support re-ingestion (idempotent — same paper ingested twice doesn't duplicate)
- **SHOULD** handle malformed or scanned PDFs gracefully with a warning

### FR-02 — Embeddings
- **MUST** generate embeddings using HuggingFace `BAAI/bge-small-en-v1.5` by default
- **MUST** persist embeddings to ChromaDB in `data/chroma_db/`
- **MUST** support switching embedding model via environment variable `EMBEDDING_MODEL`
- **SHOULD** cache embeddings to avoid re-computing on restart

### FR-03 — Retrieval
- **MUST** retrieve top-K (default K=5) semantically relevant chunks for a given query
- **MUST** support MMR (Maximal Marginal Relevance) for result diversity
- **MUST** return chunk metadata (source paper, page, section) alongside content
- **SHOULD** allow configuring K and retrieval strategy via environment variable

### FR-04 — LLM Integration
- **MUST** use Ollama as local LLM runtime (zero API cost, runs on NVIDIA GPU)
- **MUST** support `mistral:7b` as default model (fits in 4GB VRAM, quantized Q4)
- **MUST** support `llama3.1:8b` as alternative model via `OLLAMA_MODEL` env var
- **MUST** connect to Ollama via `langchain-ollama` (`OllamaLLM`)
- **MUST** format prompts to instruct the LLM to answer only from retrieved context
- **MUST** include citation instructions: response must name the source paper and year
- **SHOULD** expose model selection in the Streamlit UI (dropdown of available Ollama models)
- **SHOULD** support optional OpenAI fallback via `LLM_PROVIDER=openai` env var for users without GPU

### FR-05 — Response Format
- **MUST** return a structured response containing:
  - `answer`: the LLM-generated response
  - `sources`: list of cited papers (title, authors, year, arXiv ID)
  - `context_chunks`: the retrieved chunks used (for transparency)
- **MUST** refuse to answer (gracefully) if no relevant context is found

### FR-06 — RAGAS Evaluation
- **MUST** provide an evaluation script `evaluation/eval.py`
- **MUST** run RAGAS metrics on a curated test set of ≥20 question-answer pairs
- **MUST** report: `faithfulness`, `answer_relevancy`, `context_precision`
- **MUST** output results as JSON to `evaluation/results/ragas_scores.json`
- **MUST** configure RAGAS to use the local Ollama LLM as judge (via `langchain_ollama`)
- **SHOULD** display results as a visual summary in Streamlit sidebar

### FR-07 — Streamlit Interface
- **MUST** provide a chat interface at `app/main.py`
- **MUST** display conversation history within a session
- **MUST** show cited sources for each response
- **MUST** include a paper browser (list of indexed papers with metadata)
- **SHOULD** display the latest RAGAS scores in the sidebar
- **SHOULD** allow the user to select Ollama model from the UI (dropdown)

### FR-08 — CLI Tooling
- **MUST** provide CLI scripts for:
  - `python src/ingestion.py` — ingest all PDFs
  - `python src/embeddings.py` — generate and persist embeddings
  - `python evaluation/eval.py` — run RAGAS evaluation
  - `streamlit run app/main.py` — launch UI

### FR-09 — Paper Corpus
- **MUST** include ≥20 landmark AI/ML papers in `data/papers/`
- **MUST** provide a `data/papers_metadata.json` with structured metadata for each paper
- **SHOULD** provide a `scripts/download_papers.py` script to automate arXiv download

---

## Non-Functional Requirements

### NFR-01 — Performance
- Query-to-response latency ≤ 10s on a standard laptop (M1/M2 or equivalent)
- Ingestion of 25 papers (full corpus) completes in ≤ 5 minutes on first run

### NFR-02 — Quality (RAGAS thresholds)
- `faithfulness` ≥ 0.85 — answers must be grounded in retrieved context
- `answer_relevancy` ≥ 0.80 — answers must address the question
- `context_precision` ≥ 0.75 — retrieved chunks must be on-topic

### NFR-03 — Reproducibility
- Docker image must produce identical results across environments
- All dependencies pinned in `requirements.txt`
- `PYTHONHASHSEED` set in Docker for deterministic behavior

### NFR-04 — Observability
- Retrieval step logs: query, top-K scores, source papers
- LLM step logs: provider, model, prompt token count, response time
- Evaluation step logs: per-question scores and aggregate

### NFR-05 — Security
- API keys loaded exclusively from environment variables (never hardcoded)
- `.env` is in `.gitignore`
- No sensitive data in Docker image layers

### NFR-06 — Cost
- All components run locally with zero API cost
- Embeddings: HuggingFace local model (free)
- LLM: Ollama local inference (free, requires NVIDIA GPU 4GB+)
- Vector store: ChromaDB on disk (free)
- RAGAS evaluation: uses same local Ollama LLM as judge (free)

### NFR-07 — Maintainability
- LLM access via `langchain-ollama` `OllamaLLM` — easy to swap model without code change
- Embedding provider abstraction behind a single interface (`BaseEmbedder`)
- Each module testable in isolation with mocked dependencies
- Ollama model name configurable via `OLLAMA_MODEL` env var (default: `mistral:7b`)

---

## Constraints

| Constraint | Value |
|---|---|
| Python version | 3.11+ |
| LLM runtime | Ollama (local, must be running on `localhost:11434`) |
| Default LLM model | `mistral:7b` (Q4_K_M, ~4.4GB VRAM) |
| GPU requirement | NVIDIA 4GB+ VRAM (for acceptable inference speed) |
| ChromaDB | Local persistent (no cloud) |
| Vector store | ChromaDB only (v1.0) |
| Deploy target | Hugging Face Spaces (free tier) — Ollama not available; use CPU-only fallback or pre-built demo |
| Paper format | PDF only |
| Language | English papers only |

---

## Out of Scope (v1.0)

- Real-time arXiv ingestion or paper search
- Multi-user sessions / authentication
- Fine-tuned embedding models
- Hybrid search (keyword + semantic)
- Production database (PostgreSQL, Pinecone, etc.)
- Mobile interface

---

## Assumptions

1. User has at least one API key (OpenAI or Google AI Studio) configured in `.env`
2. PDFs are clean (text-layer PDFs from arXiv, not scans)
3. HuggingFace model can run on CPU within HF Spaces free tier memory
4. Corpus is static for v1.0 (no live updates)

---

## Acceptance Criteria Summary

| ID | Criterion | Verification |
|---|---|---|
| AC-01 | All 25 papers ingested without errors | `python src/ingestion.py` exits 0 |
| AC-02 | Query returns answer with ≥1 source citation | Manual test + unit test |
| AC-03 | RAGAS faithfulness ≥ 0.85 | `evaluation/eval.py` output |
| AC-04 | RAGAS answer_relevancy ≥ 0.80 | `evaluation/eval.py` output |
| AC-05 | RAGAS context_precision ≥ 0.75 | `evaluation/eval.py` output |
| AC-06 | Streamlit app loads and responds | `streamlit run app/main.py` |
| AC-07 | Docker image builds and runs | `docker build && docker run` |
| AC-08 | CI pipeline passes on main | GitHub Actions green |
| AC-09 | HF Spaces demo accessible | Public URL live |
