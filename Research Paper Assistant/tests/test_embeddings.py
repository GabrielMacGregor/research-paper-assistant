"""Unit tests for src/embeddings.py — mocked embedder and ChromaDB."""

from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from src.embeddings import embed_and_store


@pytest.fixture
def settings():
    return Settings(
        chroma_path="data/chroma_db_test",
        chroma_collection="test_collection",
        embedding_device="cpu",
    )


def _make_chunk(arxiv_id: str, chunk_index: int, text: str = "Sample text.") -> dict:
    return {
        "text": text,
        "metadata": {
            "paper_id": arxiv_id,
            "arxiv_id": arxiv_id,
            "title": "Test Paper",
            "authors": "Test Author et al.",
            "year": 2024,
            "topic": "Testing",
            "page": 1,
            "chunk_index": chunk_index,
        },
    }


@pytest.fixture
def two_chunks():
    return [_make_chunk("1706.03762", 0), _make_chunk("1706.03762", 1)]


def test_embed_and_store_adds_new_chunks(two_chunks, settings):
    mock_embedder = MagicMock()
    mock_embedder.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": []}
    mock_collection.count.return_value = 2

    with patch("src.embeddings.get_embedder", return_value=mock_embedder), \
         patch("src.embeddings.get_collection", return_value=mock_collection):
        added = embed_and_store(two_chunks, settings)

    assert added == 2
    mock_collection.add.assert_called_once()


def test_embed_and_store_idempotent(two_chunks, settings):
    mock_embedder = MagicMock()
    mock_collection = MagicMock()
    mock_collection.get.return_value = {
        "ids": ["1706.03762_chunk_0", "1706.03762_chunk_1"]
    }
    mock_collection.count.return_value = 2

    with patch("src.embeddings.get_embedder", return_value=mock_embedder), \
         patch("src.embeddings.get_collection", return_value=mock_collection):
        added = embed_and_store(two_chunks, settings)

    assert added == 0
    mock_collection.add.assert_not_called()


def test_embed_and_store_partial_existing(settings):
    chunks = [
        _make_chunk("1706.03762", 0),
        _make_chunk("1706.03762", 1),
        _make_chunk("1706.03762", 2),
    ]
    mock_embedder = MagicMock()
    mock_embedder.embed_documents.return_value = [[0.3] * 384]

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": ["1706.03762_chunk_0"]}  # 1 exists, 2 new
    mock_collection.count.return_value = 3

    with patch("src.embeddings.get_embedder", return_value=mock_embedder), \
         patch("src.embeddings.get_collection", return_value=mock_collection):
        added = embed_and_store(chunks, settings)

    assert added == 2


def test_embed_and_store_empty_chunks(settings):
    with patch("src.embeddings.get_embedder"), patch("src.embeddings.get_collection"):
        added = embed_and_store([], settings)
    assert added == 0


def test_embed_and_store_chunk_ids_are_deterministic(two_chunks, settings):
    mock_embedder = MagicMock()
    mock_embedder.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": []}
    mock_collection.count.return_value = 2

    captured_ids = []

    def capture_add(**kwargs):
        captured_ids.extend(kwargs.get("ids", []))

    mock_collection.add.side_effect = capture_add

    with patch("src.embeddings.get_embedder", return_value=mock_embedder), \
         patch("src.embeddings.get_collection", return_value=mock_collection):
        embed_and_store(two_chunks, settings)

    assert captured_ids == ["1706.03762_chunk_0", "1706.03762_chunk_1"]
