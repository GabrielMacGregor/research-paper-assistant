# Phase 4 Plan — Streamlit Interface

> Phase: 4 | Status: ready | Created: 2026-05-19 | Depends on: Phase 2, Phase 3

## Goal

Interactive Streamlit app: streaming chat with citations, paper browser sidebar, and RAGAS evaluation scores panel. Zero crashes if Ollama / ChromaDB / scores are not yet available.

## Pre-conditions

- Phase 2 complete: `src/pipeline.ask()` works
- `make install` run (streamlit added in this phase)
- Ollama optional for UI to render (required to answer questions)

## Architecture

```
src/pipeline.py          ← NEW: ask_stream() returns (sources, chunks, generator)
app/main.py              ← st.set_page_config + sidebar + main area
app/components/
  chat.py                ← streaming chat via st.write_stream()
  sources.py             ← inline expander showing paper citations
  paper_browser.py       ← sidebar: all 25 papers with metadata
  eval_dashboard.py      ← sidebar: RAGAS score metrics
```

### Streaming Design

1. `ask_stream(query, settings)` in `pipeline.py` returns `(sources, chunks, generator)`
2. Retrieval runs first (fast) — sources appear immediately before streaming starts
3. `st.write_stream(generator)` streams tokens and returns the full answer string
4. Full answer stored in `st.session_state` when stream completes

State: `st.session_state.messages` list of `{"role", "content", "sources?"}` dicts.

---

## Execution Waves

---

### Wave 1 — Setup (run in parallel)

#### Task 1.1 — Add `streamlit` to `requirements.txt`

Append after the ragas block:

```
# UI
streamlit==1.45.1
```

#### Task 1.2 — Create `app/__init__.py` and `app/components/__init__.py`

Both empty files.

---

### Wave 2 — Add `ask_stream()` to `src/pipeline.py`

Append to the **end** of the existing `src/pipeline.py` (after the `ask()` function, before `if __name__ == "__main__"`):

```python
from collections.abc import Generator


def ask_stream(
    query: str,
    settings: Settings | None = None,
) -> tuple[list[Source], list[dict], Generator[str, None, None]]:
    """
    Streaming variant of ask().
    Returns (sources, context_chunks, token_generator) so the caller can
    render sources before streaming starts, then yield tokens into st.write_stream.
    """
    if settings is None:
        settings = Settings()

    chunks = retrieve(query, settings)

    if not chunks:
        logger.warning("No relevant chunks found for query.")

        def _no_context() -> Generator[str, None, None]:
            yield NO_CONTEXT_REPLY

        return [], [], _no_context()

    context = _build_context(chunks)
    sources = _extract_sources(chunks)
    llm = get_llm(settings)
    messages = RAG_PROMPT.format_messages(context=context, question=query)

    def _stream() -> Generator[str, None, None]:
        for chunk in llm.stream(messages):
            yield chunk.content

    return sources, chunks, _stream()
```

**Note**: `ask()` is unchanged — all Phase 3 tests stay green.

---

### Wave 3 — Sidebar components (no pipeline dependency, run in parallel)

#### Task 3.1 — Create `app/components/eval_dashboard.py`

```python
"""Sidebar widget displaying RAGAS evaluation scores."""

import json
from pathlib import Path

import streamlit as st

_SCORES_PATH = Path("evaluation/results/ragas_scores.json")
_THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
}
_LABELS = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer Relevancy",
    "context_precision": "Context Precision",
}


def load_scores(path: Path = _SCORES_PATH) -> dict | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_eval_dashboard() -> None:
    st.subheader("RAGAS Evaluation")
    data = load_scores()

    if data is None:
        st.info("No scores yet. Run `make eval` after populating ChromaDB.")
        return

    agg = data.get("aggregate", {})
    n = agg.get("n_questions", 0)
    st.caption(f"n={n} questions | local Ollama judge")

    for key, label in _LABELS.items():
        score = agg.get(key)
        if score is None:
            continue
        threshold = _THRESHOLDS[key]
        delta = round(score - threshold, 3)
        st.metric(
            label=label,
            value=f"{score:.3f}",
            delta=f"{delta:+.3f} vs ≥{threshold}",
            delta_color="normal",
        )
```

#### Task 3.2 — Create `app/components/paper_browser.py`

```python
"""Sidebar widget listing all indexed papers."""

import json
from pathlib import Path

import streamlit as st

_METADATA_PATH = Path("data/papers_metadata.json")


def load_papers(path: Path = _METADATA_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_paper_browser() -> None:
    st.subheader("Indexed Papers")
    papers = load_papers()

    if not papers:
        st.warning("No papers indexed. Run `make pipeline` first.")
        return

    st.caption(f"{len(papers)} papers in knowledge base")

    for paper in papers:
        title_short = paper["title"][:48] + ("…" if len(paper["title"]) > 48 else "")
        with st.expander(f"{title_short} ({paper['year']})"):
            authors = paper["authors"]
            if isinstance(authors, list):
                author_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    author_str += " et al."
            else:
                author_str = str(authors)
            st.markdown(f"**Authors:** {author_str}")
            st.markdown(f"**Topic:** {paper['topic']}")
            arxiv_id = paper["arxiv_id"]
            st.markdown(
                f"**arXiv:** [{arxiv_id}](https://arxiv.org/abs/{arxiv_id})"
            )
```

---

### Wave 4 — Chat components (run in parallel)

#### Task 4.1 — Create `app/components/sources.py`

```python
"""Inline citations component rendered below each assistant message."""

import streamlit as st


def render_sources(sources: list[dict]) -> None:
    """Render a collapsible sources block.

    Args:
        sources: list of dicts with keys title, authors, year, arxiv_id.
    """
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for s in sources:
            arxiv_id = s.get("arxiv_id", "")
            title = s.get("title", "Unknown")
            year = s.get("year", "")
            authors = s.get("authors", "")
            st.markdown(
                f"**{title}** ({year})  \n"
                f"_{authors}_  \n"
                f"[arxiv.org/abs/{arxiv_id}](https://arxiv.org/abs/{arxiv_id})"
            )
```

#### Task 4.2 — Create `app/components/chat.py`

```python
"""Streaming chat interface with conversation history and citations."""

import streamlit as st

from app.components.sources import render_sources
from config.settings import Settings
from src.pipeline import ask_stream


def _sources_to_dicts(sources) -> list[dict]:
    """Convert Source dataclasses to plain dicts for session_state storage."""
    return [
        {
            "title": s.title,
            "authors": s.authors,
            "year": s.year,
            "arxiv_id": s.arxiv_id,
        }
        for s in sources
    ]


def render_chat(settings: Settings) -> None:
    st.title("📚 Research Paper Assistant")
    st.caption(
        "Ask questions about 25 landmark AI/ML papers — "
        f"powered by **{settings.ollama_model}** via Ollama"
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Replay conversation history on every rerun
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                render_sources(msg["sources"])

    # New user input
    if prompt := st.chat_input("Ask about transformers, RAG, LoRA, RLHF..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Searching papers..."):
                    sources_raw, _chunks, token_gen = ask_stream(prompt, settings)
                sources = _sources_to_dicts(sources_raw)

                # Show sources before streaming starts
                if sources:
                    render_sources(sources)

                # Stream tokens — returns full answer string when complete
                answer = st.write_stream(token_gen)

            except Exception as exc:
                answer = (
                    "Could not reach Ollama. Make sure `ollama serve` is running "
                    f"and `{settings.ollama_model}` is pulled.\n\n"
                    f"```\n{exc}\n```"
                )
                sources = []
                st.markdown(answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )
```

---

### Wave 5 — App entrypoint

#### Task 5.1 — Create `app/main.py`

```python
"""Streamlit entrypoint — Research Paper Assistant."""

import streamlit as st

from app.components.chat import render_chat
from app.components.eval_dashboard import render_eval_dashboard
from app.components.paper_browser import render_paper_browser
from config.settings import Settings

# MUST be first Streamlit call
st.set_page_config(
    page_title="Research Paper Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_settings() -> Settings:
    return Settings()


def main() -> None:
    settings = get_settings()

    with st.sidebar:
        render_eval_dashboard()
        st.divider()
        render_paper_browser()

    render_chat(settings)


if __name__ == "__main__":
    main()
```

---

### Wave 6 — Tests + tooling (run in parallel)

#### Task 6.1 — Create `tests/test_app.py`

```python
"""Unit tests for Streamlit component data-loading functions."""

import json

import pytest

from app.components.eval_dashboard import load_scores
from app.components.paper_browser import load_papers


def test_load_scores_returns_none_when_missing(tmp_path):
    assert load_scores(tmp_path / "scores.json") is None


def test_load_scores_parses_aggregate(tmp_path):
    f = tmp_path / "scores.json"
    data = {
        "aggregate": {
            "faithfulness": 0.89,
            "answer_relevancy": 0.83,
            "context_precision": 0.78,
            "n_questions": 25,
        }
    }
    f.write_text(json.dumps(data), encoding="utf-8")
    result = load_scores(f)
    assert result["aggregate"]["faithfulness"] == pytest.approx(0.89)
    assert result["aggregate"]["n_questions"] == 25


def test_load_papers_returns_empty_when_missing(tmp_path):
    assert load_papers(tmp_path / "metadata.json") == []


def test_load_papers_returns_all_25():
    papers = load_papers()
    assert len(papers) == 25


def test_load_papers_have_required_fields():
    papers = load_papers()
    for p in papers:
        assert "arxiv_id" in p
        assert "title" in p
        assert "authors" in p
        assert "year" in p
        assert "topic" in p


def test_load_scores_all_three_metrics(tmp_path):
    f = tmp_path / "scores.json"
    data = {
        "aggregate": {
            "faithfulness": 0.88,
            "answer_relevancy": 0.81,
            "context_precision": 0.76,
            "n_questions": 5,
        }
    }
    f.write_text(json.dumps(data), encoding="utf-8")
    result = load_scores(f)
    agg = result["aggregate"]
    assert "faithfulness" in agg
    assert "answer_relevancy" in agg
    assert "context_precision" in agg
```

#### Task 6.2 — Add `ask_stream` test to `tests/test_pipeline.py`

Append to the existing `tests/test_pipeline.py`:

```python
def test_ask_stream_returns_sources_and_generator(settings):
    mock_chunks = [
        {
            "text": "Attention computes dot products.",
            "metadata": {
                "title": "Attention Is All You Need",
                "authors": "Vaswani et al.",
                "year": 2017,
                "arxiv_id": "1706.03762",
                "page": 1,
            },
            "score": 0.9,
        }
    ]
    mock_llm = MagicMock()
    mock_llm.stream.return_value = [MagicMock(content="token1"), MagicMock(content="token2")]

    with patch("src.pipeline.retrieve", return_value=mock_chunks):
        with patch("src.pipeline.get_llm", return_value=mock_llm):
            from src.pipeline import ask_stream
            sources, chunks, gen = ask_stream("What is attention?", settings)

    assert len(sources) == 1
    assert sources[0].title == "Attention Is All You Need"
    tokens = list(gen)
    assert tokens == ["token1", "token2"]


def test_ask_stream_no_context_yields_fallback(settings):
    with patch("src.pipeline.retrieve", return_value=[]):
        from src.pipeline import ask_stream
        sources, chunks, gen = ask_stream("unknown question", settings)

    assert sources == []
    assert chunks == []
    assert list(gen) == [NO_CONTEXT_REPLY]
```

#### Task 6.3 — Update `Makefile`

Update `.PHONY` line and add `ui` target:

```makefile
.PHONY: install download ingest embed pipeline ask eval eval-sample ui test lint format check

ui:
	streamlit run app/main.py
```

---

## Verification Steps

```bash
# 1. Install streamlit
pip install -r requirements.txt

# 2. Tests (all mocked, no Ollama needed)
pytest tests/ -v

# 3. Lint (including app/)
ruff check src/ tests/ scripts/ evaluation/ app/

# 4. Launch UI
make ui
# → open http://localhost:8501
```

## UAT Checklist

- [ ] `pytest tests/` — all tests pass including `test_app.py`
- [ ] `ruff check` — lint clean
- [ ] `streamlit run app/main.py` starts without error
- [ ] Sidebar: "No scores yet" when `ragas_scores.json` absent
- [ ] Sidebar: "No papers indexed" when `papers_metadata.json` absent
- [ ] Sidebar: all 25 papers visible when metadata present
- [ ] Chat: question → spinner → sources appear → answer streams token by token
- [ ] Conversation history persists (scroll up sees prior Q&A)
- [ ] Ollama offline → friendly error message in chat, app keeps running
- [ ] RAGAS scores show in sidebar when `ragas_scores.json` present

## Phase Complete Criteria

All UAT items checked + tests green + lint clean.
Next: `/gsd:plan-phase 5` — Docker + CI/CD + Hugging Face Spaces deploy.
