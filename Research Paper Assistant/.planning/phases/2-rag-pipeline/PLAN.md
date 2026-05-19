# Phase 2 Plan — RAG Pipeline

> Phase: 2 | Status: ready | Created: 2026-05-19 | Depends on: Phase 1

## Goal

End-to-end RAG pipeline: user query → semantic retrieval (MMR) → prompt construction → ChatOllama (local) → structured response with paper citations. Runnable via `python src/pipeline.py --query "..."`.

## Pre-conditions

- Phase 1 complete: ChromaDB populated (`data/chroma_db/` exists with ≥ 500 chunks)
- `make install` run (all dependencies installed)
- Ollama installed and `mistral:7b` pulled (`ollama pull mistral:7b`)

## Architecture

```
query string
    │
    ▼
src/retriever.py
  ├── embed query (HuggingFace bge-small-en-v1.5)
  ├── ChromaDB.query() → top K*3 candidates
  └── MMR selection → top K diverse chunks
    │
    ▼
src/prompts.py
  └── ChatPromptTemplate(system=context+instructions, human=question)
    │
    ▼
src/llm.py
  └── ChatOllama(model=mistral:7b, base_url=localhost:11434)
    │
    ▼
src/pipeline.py
  └── RAGResponse(answer, sources, context_chunks, query)
```

## Execution Waves

---

### Wave 1 — Prompts (no dependencies)

#### Task 1.1 — Create `src/prompts.py`

```python
"""RAG prompt templates."""

from langchain_core.prompts import ChatPromptTemplate

_SYSTEM = """\
You are a research assistant specializing in AI/ML papers.
Answer the question ONLY using the context below — do not use outside knowledge.
Always cite the paper(s) you drew from (title and year) at the end of your answer.
If the context does not contain enough information to answer, respond with exactly:
"I couldn't find relevant information in the indexed papers."

Context:
{context}
"""

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "{question}"),
])
```

---

### Wave 2 — LLM + Retriever (run in parallel)

#### Task 2.1 — Create `src/llm.py`

```python
"""Local LLM wrapper via Ollama + ChatOllama."""

from langchain_ollama import ChatOllama

from config.settings import Settings


def get_llm(settings: Settings) -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
    )
```

#### Task 2.2 — Create `src/retriever.py`

This module:
1. Loads the embedder and ChromaDB collection (same as Phase 1)
2. Embeds the query
3. Fetches top `K * fetch_multiplier` candidates by cosine similarity
4. Applies MMR (Maximal Marginal Relevance) to return K diverse results

```python
"""Semantic retrieval with MMR from ChromaDB."""

import logging
from typing import Any

import numpy as np

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import Settings

logger = logging.getLogger(__name__)

FETCH_MULTIPLIER = 3  # retrieve 3x candidates before MMR filtering


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    return float(np.dot(a_arr, b_arr) / denom) if denom > 0 else 0.0


def _mmr(
    query_embedding: list[float],
    candidates: list[dict[str, Any]],
    k: int,
    lambda_mult: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Maximal Marginal Relevance selection.
    lambda_mult=1 → pure similarity; lambda_mult=0 → pure diversity.
    """
    if len(candidates) <= k:
        return candidates

    embs = [c["embedding"] for c in candidates]
    query_sims = [_cosine_sim(query_embedding, e) for e in embs]

    selected: list[int] = []
    remaining = list(range(len(candidates)))

    while len(selected) < k and remaining:
        if not selected:
            best = max(remaining, key=lambda i: query_sims[i])
        else:
            selected_embs = [embs[i] for i in selected]
            best = max(
                remaining,
                key=lambda i: (
                    lambda_mult * query_sims[i]
                    - (1 - lambda_mult) * max(_cosine_sim(embs[i], s) for s in selected_embs)
                ),
            )
        selected.append(best)
        remaining.remove(best)

    return [candidates[i] for i in selected]


def retrieve(
    query: str,
    settings: Settings,
    use_mmr: bool = True,
) -> list[dict[str, Any]]:
    """
    Retrieve top-K relevant chunks for a query.
    Returns list of {text, metadata, score} dicts.
    """
    embedder = HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": settings.embedding_device},
        encode_kwargs={"normalize_embeddings": True},
    )
    query_embedding = embedder.embed_query(query)

    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_collection(settings.chroma_collection)

    fetch_k = settings.top_k * FETCH_MULTIPLIER
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(fetch_k, collection.count()),
        include=["documents", "metadatas", "distances", "embeddings"],
    )

    candidates = [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score": 1.0 - results["distances"][0][i],  # distance → similarity
            "embedding": results["embeddings"][0][i],
        }
        for i in range(len(results["documents"][0]))
    ]

    if use_mmr:
        selected = _mmr(query_embedding, candidates, k=settings.top_k)
    else:
        selected = candidates[: settings.top_k]

    # Strip raw embeddings from output (not needed downstream)
    for chunk in selected:
        chunk.pop("embedding", None)

    logger.info("Retrieved %d chunks for query: %s", len(selected), query[:60])
    return selected
```

---

### Wave 3 — Pipeline (depends on Wave 1 + Wave 2)

#### Task 3.1 — Create `src/pipeline.py`

```python
"""RAG pipeline: query → retrieve → prompt → LLM → structured response."""

import argparse
import logging
from dataclasses import dataclass, field

from config.settings import Settings
from src.llm import get_llm
from src.prompts import RAG_PROMPT
from src.retriever import retrieve

logger = logging.getLogger(__name__)

NO_CONTEXT_REPLY = "I couldn't find relevant information in the indexed papers."


@dataclass
class Source:
    title: str
    authors: str
    year: int
    arxiv_id: str


@dataclass
class RAGResponse:
    answer: str
    sources: list[Source]
    context_chunks: list[dict]
    query: str = ""


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        parts.append(
            f"[{i}] {meta['title']} ({meta['year']}) — {meta['authors']}\n"
            f"Page {meta['page']}:\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def _extract_sources(chunks: list[dict]) -> list[Source]:
    """Deduplicate and build Source objects from chunk metadata."""
    seen: set[str] = set()
    sources: list[Source] = []
    for chunk in chunks:
        meta = chunk["metadata"]
        arxiv_id = meta["arxiv_id"]
        if arxiv_id not in seen:
            seen.add(arxiv_id)
            sources.append(Source(
                title=meta["title"],
                authors=meta["authors"],
                year=meta["year"],
                arxiv_id=arxiv_id,
            ))
    return sources


def ask(query: str, settings: Settings | None = None) -> RAGResponse:
    """Full RAG pipeline: query → answer with citations."""
    if settings is None:
        settings = Settings()

    chunks = retrieve(query, settings)

    if not chunks:
        logger.warning("No relevant chunks found for query.")
        return RAGResponse(
            answer=NO_CONTEXT_REPLY,
            sources=[],
            context_chunks=[],
            query=query,
        )

    context = _build_context(chunks)
    llm = get_llm(settings)
    messages = RAG_PROMPT.format_messages(context=context, question=query)
    response = llm.invoke(messages)
    answer = response.content

    return RAGResponse(
        answer=answer,
        sources=_extract_sources(chunks),
        context_chunks=chunks,
        query=query,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ask a question about AI/ML papers.")
    parser.add_argument("--query", required=True, help="Question to ask")
    parser.add_argument("--no-mmr", action="store_true", help="Disable MMR, use plain similarity")
    args = parser.parse_args()

    settings = Settings()
    response = ask(args.query, settings)

    print(f"\n{'='*60}")
    print(f"Query: {response.query}")
    print(f"{'='*60}")
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nSources ({len(response.sources)}):")
    for s in response.sources:
        print(f"  • {s.title} ({s.year}) — arxiv:{s.arxiv_id}")
    print(f"\nContext chunks used: {len(response.context_chunks)}")
```

---

### Wave 4 — Update dependencies + conftest

#### Task 4.1 — Add `numpy` to `requirements.txt`

Add this line under `# Utils` in `requirements.txt`:
```
numpy>=1.26,<3.0
```

(numpy is already a transitive dep of sentence-transformers but we pin it explicitly since `src/retriever.py` imports it directly)

#### Task 4.2 — Update `tests/conftest.py`

Add `langchain_ollama` stub if not already there (it is — from Phase 1 conftest).
No changes needed; `langchain_ollama` is already in `_HEAVY_MOCKS`.

---

### Wave 5 — Tests (run in parallel)

#### Task 5.1 — Create `tests/test_retriever.py`

```python
"""Unit tests for src/retriever.py."""

from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings


@pytest.fixture
def settings():
    return Settings(top_k=3, embedding_device="cpu")


def _make_query_results(n: int = 6) -> dict:
    """Fake ChromaDB query() output with n results."""
    return {
        "documents": [[f"chunk text {i}" for i in range(n)]],
        "metadatas": [[{
            "arxiv_id": f"paper_{i % 3}",
            "title": f"Paper {i % 3}",
            "authors": "Author et al.",
            "year": 2020 + i,
            "page": i + 1,
            "chunk_index": i,
        } for i in range(n)]],
        "distances": [[(i * 0.05) for i in range(n)]],
        "embeddings": [[[float(i) / 10] * 10 for i in range(n)]],
    }


def test_retrieve_returns_top_k(settings):
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 10

    mock_collection = MagicMock()
    mock_collection.count.return_value = 20
    mock_collection.query.return_value = _make_query_results(n=9)

    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("src.retriever.HuggingFaceEmbeddings", return_value=mock_embedder), \
         patch("src.retriever.chromadb.PersistentClient", return_value=mock_client):
        from src.retriever import retrieve
        results = retrieve("what is attention?", settings, use_mmr=False)

    assert len(results) == settings.top_k


def test_retrieve_mmr_returns_top_k(settings):
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.5] * 10

    mock_collection = MagicMock()
    mock_collection.count.return_value = 20
    mock_collection.query.return_value = _make_query_results(n=9)

    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("src.retriever.HuggingFaceEmbeddings", return_value=mock_embedder), \
         patch("src.retriever.chromadb.PersistentClient", return_value=mock_client):
        from src.retriever import retrieve
        results = retrieve("what is attention?", settings, use_mmr=True)

    assert len(results) == settings.top_k


def test_retrieve_strips_embeddings_from_output(settings):
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 10

    mock_collection = MagicMock()
    mock_collection.count.return_value = 10
    mock_collection.query.return_value = _make_query_results(n=3)

    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("src.retriever.HuggingFaceEmbeddings", return_value=mock_embedder), \
         patch("src.retriever.chromadb.PersistentClient", return_value=mock_client):
        from src.retriever import retrieve
        results = retrieve("test query", settings, use_mmr=False)

    for chunk in results:
        assert "embedding" not in chunk, "Raw embeddings must not leak into output"


def test_retrieve_result_has_expected_keys(settings):
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 10

    mock_collection = MagicMock()
    mock_collection.count.return_value = 10
    mock_collection.query.return_value = _make_query_results(n=3)

    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("src.retriever.HuggingFaceEmbeddings", return_value=mock_embedder), \
         patch("src.retriever.chromadb.PersistentClient", return_value=mock_client):
        from src.retriever import retrieve
        results = retrieve("test", settings, use_mmr=False)

    for chunk in results:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "score" in chunk
```

#### Task 5.2 — Create `tests/test_pipeline.py`

```python
"""Unit tests for src/pipeline.py."""

from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from src.pipeline import (
    NO_CONTEXT_REPLY,
    RAGResponse,
    Source,
    _build_context,
    _extract_sources,
    ask,
)


@pytest.fixture
def settings():
    return Settings(top_k=3, embedding_device="cpu")


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "The Transformer uses multi-head attention.",
            "metadata": {
                "arxiv_id": "1706.03762",
                "title": "Attention Is All You Need",
                "authors": "Vaswani et al.",
                "year": 2017,
                "page": 3,
            },
            "score": 0.92,
        },
        {
            "text": "Self-attention allows the model to relate positions.",
            "metadata": {
                "arxiv_id": "1706.03762",
                "title": "Attention Is All You Need",
                "authors": "Vaswani et al.",
                "year": 2017,
                "page": 4,
            },
            "score": 0.87,
        },
        {
            "text": "BERT uses bidirectional transformer encoder.",
            "metadata": {
                "arxiv_id": "1810.04805",
                "title": "BERT",
                "authors": "Devlin et al.",
                "year": 2018,
                "page": 2,
            },
            "score": 0.75,
        },
    ]


def test_build_context_includes_titles(sample_chunks):
    ctx = _build_context(sample_chunks)
    assert "Attention Is All You Need" in ctx
    assert "BERT" in ctx


def test_build_context_includes_page_numbers(sample_chunks):
    ctx = _build_context(sample_chunks)
    assert "Page 3" in ctx


def test_extract_sources_deduplicates(sample_chunks):
    sources = _extract_sources(sample_chunks)
    # 3 chunks but only 2 unique papers
    assert len(sources) == 2
    arxiv_ids = [s.arxiv_id for s in sources]
    assert "1706.03762" in arxiv_ids
    assert "1810.04805" in arxiv_ids


def test_extract_sources_returns_source_objects(sample_chunks):
    sources = _extract_sources(sample_chunks)
    for s in sources:
        assert isinstance(s, Source)
        assert s.title
        assert s.year > 2000
        assert s.arxiv_id


def test_ask_returns_no_context_reply_when_no_chunks(settings):
    with patch("src.pipeline.retrieve", return_value=[]):
        response = ask("anything", settings)
    assert response.answer == NO_CONTEXT_REPLY
    assert response.sources == []
    assert response.context_chunks == []


def test_ask_returns_rag_response_with_sources(sample_chunks, settings):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="The attention mechanism uses queries and keys.")

    with patch("src.pipeline.retrieve", return_value=sample_chunks), \
         patch("src.pipeline.get_llm", return_value=mock_llm):
        response = ask("What is attention?", settings)

    assert isinstance(response, RAGResponse)
    assert response.answer == "The attention mechanism uses queries and keys."
    assert len(response.sources) == 2
    assert len(response.context_chunks) == 3


def test_ask_passes_query_to_response(sample_chunks, settings):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Some answer.")

    with patch("src.pipeline.retrieve", return_value=sample_chunks), \
         patch("src.pipeline.get_llm", return_value=mock_llm):
        response = ask("What is BERT?", settings)

    assert response.query == "What is BERT?"


def test_ask_invokes_llm_with_context_and_question(sample_chunks, settings):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Answer.")

    with patch("src.pipeline.retrieve", return_value=sample_chunks), \
         patch("src.pipeline.get_llm", return_value=mock_llm):
        ask("What is self-attention?", settings)

    mock_llm.invoke.assert_called_once()
    # Verify the prompt contains the query
    call_args = mock_llm.invoke.call_args[0][0]  # messages list
    messages_text = str(call_args)
    assert "What is self-attention?" in messages_text
```

---

### Wave 6 — Update Makefile

#### Task 6.1 — Add `ask` target to `Makefile`

Add after the `embed` target:
```makefile
ask:
	@if [ -z "$(QUERY)" ]; then echo "Usage: make ask QUERY='your question here'"; exit 1; fi
	python src/pipeline.py --query "$(QUERY)"
```

Full updated `Makefile`:
```makefile
.PHONY: install download ingest embed pipeline ask test lint format check

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

check: lint test
	@echo "All checks passed."
```

---

## Verification Steps

```bash
# 1. Install numpy (if not already from make install)
pip install "numpy>=1.26"

# 2. Run tests (mocked — no Ollama needed)
pytest tests/ -v

# 3. Lint
ruff check src/ tests/ scripts/

# 4. Manual end-to-end test (requires Ollama + ChromaDB populated)
# First: ollama serve (in another terminal)
# Then:
python src/pipeline.py --query "What is the attention mechanism?"
python src/pipeline.py --query "How does LoRA reduce the number of trainable parameters?"
python src/pipeline.py --query "What are the main differences between BERT and GPT?"
```

## UAT Checklist

- [ ] `pytest tests/` — all tests pass (including new phase 2 tests)
- [ ] `ruff check` — lint clean
- [ ] `python src/pipeline.py --query "What is attention?"` returns structured answer
- [ ] Response includes ≥1 source citation with paper title and year
- [ ] Query with no relevant context returns the `NO_CONTEXT_REPLY` message
- [ ] Switching model: `OLLAMA_MODEL=llama3.1:8b python src/pipeline.py --query "..."` works
- [ ] Response has all fields: `answer`, `sources`, `context_chunks`, `query`

## Phase Complete Criteria

All UAT items checked + tests green + lint clean.
Next: `/gsd:plan-phase 3` — RAGAS Evaluation.
