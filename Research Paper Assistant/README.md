# Research Paper Assistant

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
```

## Running RAGAS Evaluation

```bash
# Quick check — 5 questions (~5-10 min)
make eval-sample

# Full evaluation — 25 questions (~15-45 min)
make eval
```

Results are saved to:
- `evaluation/results/ragas_report.md` — human-readable score table (committed)
- `evaluation/results/ragas_scores.json` — full per-question breakdown (gitignored)

**Target thresholds:** Faithfulness ≥ 0.85 · Answer Relevancy ≥ 0.80 · Context Precision ≥ 0.75

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
scripts/
  download_papers.py     arXiv PDF downloader (rate-limited, idempotent)
src/
  ingestion.py           PDF parsing + chunking (PyMuPDF)
  embeddings.py          HuggingFace embeddings → ChromaDB
  retriever.py           semantic search + MMR
  pipeline.py            full RAG pipeline: query → answer + citations
  llm.py                 Ollama LLM wrapper
  prompts.py             system prompt template
tests/                   36 unit tests (all mocked — no GPU needed)
```

## Development

```bash
make test       # run 36 unit tests (no GPU required)
make lint       # ruff check
make check      # lint + test
```

## Implementation Status

| Phase | Description | Status |
|---|---|---|
| 1 — Data Pipeline | Download → parse → embed → ChromaDB | Complete |
| 2 — RAG Pipeline | Retrieve → prompt → Ollama → cited response | Complete |
| 3 — RAGAS Evaluation | 25 Q&A pairs + local LLM judge + score report | Complete (needs GPU to run) |
| 4 — Streamlit UI | Chat interface + paper browser + RAGAS dashboard | **Pending** |
| 5 — Infrastructure | Docker + GitHub Actions CI/CD + Hugging Face Spaces deploy | **Pending** |

## Configuration

Copy `.env.example` to `.env` to override defaults:

```env
OLLAMA_MODEL=mistral:7b
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DEVICE=cuda
TOP_K=5
```
