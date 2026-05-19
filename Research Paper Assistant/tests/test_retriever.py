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


def test_retrieve_fewer_candidates_than_k(settings):
    """When ChromaDB has fewer docs than top_k, return all available."""
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 10

    mock_collection = MagicMock()
    mock_collection.count.return_value = 2
    mock_collection.query.return_value = _make_query_results(n=2)

    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection

    with patch("src.retriever.HuggingFaceEmbeddings", return_value=mock_embedder), \
         patch("src.retriever.chromadb.PersistentClient", return_value=mock_client):
        from src.retriever import retrieve
        results = retrieve("test", settings, use_mmr=True)

    assert len(results) == 2  # only 2 available, not top_k=3
