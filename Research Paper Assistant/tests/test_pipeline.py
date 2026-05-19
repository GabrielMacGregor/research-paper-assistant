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
    assert "Page 4" in ctx


def test_build_context_includes_chunk_text(sample_chunks):
    ctx = _build_context(sample_chunks)
    assert "multi-head attention" in ctx
    assert "bidirectional transformer" in ctx


def test_extract_sources_deduplicates(sample_chunks):
    sources = _extract_sources(sample_chunks)
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


def test_extract_sources_preserves_order(sample_chunks):
    sources = _extract_sources(sample_chunks)
    assert sources[0].arxiv_id == "1706.03762"
    assert sources[1].arxiv_id == "1810.04805"


def test_ask_returns_no_context_reply_when_no_chunks(settings):
    with patch("src.pipeline.retrieve", return_value=[]):
        response = ask("anything", settings)
    assert response.answer == NO_CONTEXT_REPLY
    assert response.sources == []
    assert response.context_chunks == []


def test_ask_returns_rag_response_with_sources(sample_chunks, settings):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content="The attention mechanism uses queries and keys."
    )
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


def test_ask_invokes_llm_with_question_in_prompt(sample_chunks, settings):
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="Answer.")
    with patch("src.pipeline.retrieve", return_value=sample_chunks), \
         patch("src.pipeline.get_llm", return_value=mock_llm):
        ask("What is self-attention?", settings)

    mock_llm.invoke.assert_called_once()
    messages = mock_llm.invoke.call_args[0][0]
    assert any("What is self-attention?" in str(m) for m in messages)


def test_ask_no_context_sets_empty_query(settings):
    with patch("src.pipeline.retrieve", return_value=[]):
        response = ask("irrelevant question", settings)
    assert response.query == "irrelevant question"


def test_ask_stream_returns_sources_and_generator(sample_chunks, settings):
    mock_llm = MagicMock()
    mock_llm.stream.return_value = [
        MagicMock(content="token1"),
        MagicMock(content="token2"),
    ]
    with patch("src.pipeline.retrieve", return_value=sample_chunks), \
         patch("src.pipeline.get_llm", return_value=mock_llm):
        from src.pipeline import ask_stream
        sources, chunks, gen = ask_stream("What is attention?", settings)

    assert len(sources) == 2
    assert sources[0].title == "Attention Is All You Need"
    assert list(gen) == ["token1", "token2"]


def test_ask_stream_no_context_yields_fallback(settings):
    with patch("src.pipeline.retrieve", return_value=[]):
        from src.pipeline import ask_stream
        sources, chunks, gen = ask_stream("unknown question", settings)

    assert sources == []
    assert chunks == []
    assert list(gen) == [NO_CONTEXT_REPLY]
