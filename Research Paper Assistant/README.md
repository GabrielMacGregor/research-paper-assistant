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

Results are saved to:
- `evaluation/results/ragas_report.md` — human-readable score table
- `evaluation/results/ragas_scores.json` — full per-question breakdown

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
  pipeline.py            full RAG pipeline + streaming variant
  llm.py                 Ollama LLM wrapper
  prompts.py             system prompt template
tests/                   44 unit tests (all mocked — no GPU needed)
```

## Development

```bash
make test       # run 44 unit tests (no GPU required)
make lint       # ruff check
make check      # lint + test
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
