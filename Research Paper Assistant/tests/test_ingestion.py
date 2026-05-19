"""Unit tests for src/ingestion.py — no real PDFs or filesystem required."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from src.ingestion import chunk_pages, extract_pages, load_metadata


@pytest.fixture
def settings():
    return Settings(chunk_size=100, chunk_overlap=10)


@pytest.fixture
def sample_metadata():
    return {
        "arxiv_id": "1706.03762",
        "title": "Attention Is All You Need",
        "authors": ["Vaswani", "Shazeer", "Parmar", "Uszkoreit"],
        "year": 2017,
        "topic": "Transformers",
    }


@pytest.fixture
def sample_pages():
    long_sentence = "We propose a new simple network architecture, the Transformer. "
    return [
        {"page": 1, "text": long_sentence * 15},
        {"page": 2, "text": "The dominant sequence transduction models are based on encoder-decoder. " * 15},
    ]


def test_load_metadata_indexes_by_arxiv_id(tmp_path):
    meta = [{"arxiv_id": "1706.03762", "title": "Test", "authors": ["A"], "year": 2017, "topic": "T"}]
    meta_file = tmp_path / "papers_metadata.json"
    meta_file.write_text(json.dumps(meta))
    result = load_metadata(meta_file)
    assert "1706.03762" in result
    assert result["1706.03762"]["title"] == "Test"


def test_load_metadata_all_25_papers():
    result = load_metadata(Path("data/papers_metadata.json"))
    assert len(result) == 25


def test_chunk_pages_returns_nonempty_chunks(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    assert len(chunks) > 0


def test_chunk_pages_metadata_fields_present(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    for chunk in chunks:
        assert "text" in chunk
        meta = chunk["metadata"]
        assert meta["arxiv_id"] == "1706.03762"
        assert meta["title"] == "Attention Is All You Need"
        assert meta["year"] == 2017
        assert "page" in meta
        assert "chunk_index" in meta
        assert "authors" in meta


def test_chunk_pages_sequential_index(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    indices = [c["metadata"]["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_pages_no_empty_text(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    for chunk in chunks:
        assert chunk["text"].strip(), "Chunk text must not be empty"


def test_chunk_pages_authors_truncated_with_et_al():
    meta = {
        "arxiv_id": "test",
        "title": "Test Paper",
        "authors": ["A", "B", "C", "D", "E"],  # 5 authors -> "A, B, C et al."
        "year": 2024,
        "topic": "Test",
    }
    pages = [{"page": 1, "text": "Some content here to chunk. " * 20}]
    chunks = chunk_pages(pages, meta, chunk_size=100, chunk_overlap=10)
    assert "et al." in chunks[0]["metadata"]["authors"]


def test_extract_pages_skips_empty_pages():
    mock_page_with_text = MagicMock()
    mock_page_with_text.get_text.return_value = "Some meaningful content."
    mock_empty_page = MagicMock()
    mock_empty_page.get_text.return_value = "   \n  "

    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page_with_text, mock_empty_page]))
    mock_doc.close = MagicMock()

    with patch("src.ingestion.pymupdf.open", return_value=mock_doc):
        pages = extract_pages(Path("fake.pdf"))

    assert len(pages) == 1
    assert pages[0]["text"] == "Some meaningful content."
    assert pages[0]["page"] == 1
