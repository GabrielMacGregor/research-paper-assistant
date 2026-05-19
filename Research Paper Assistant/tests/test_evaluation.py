"""Unit tests for evaluation/eval.py — mocked RAGAS and pipeline."""

import json
from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings


@pytest.fixture
def settings():
    return Settings(embedding_device="cpu")


@pytest.fixture
def sample_questions():
    return [
        {
            "id": "q01",
            "question": "What is the attention mechanism?",
            "reference_answer": "Attention computes weighted sum of values.",
            "category": "Transformers",
            "papers": ["1706.03762"],
        },
        {
            "id": "q02",
            "question": "What is RAG?",
            "reference_answer": "RAG combines retrieval with generation.",
            "category": "Retrieval",
            "papers": ["2005.11401"],
        },
    ]


@pytest.fixture
def mock_rag_response():
    from src.pipeline import RAGResponse, Source

    return RAGResponse(
        answer="The attention mechanism uses query-key-value.",
        sources=[
            Source(
                title="Attention Is All You Need",
                authors="Vaswani et al.",
                year=2017,
                arxiv_id="1706.03762",
            )
        ],
        context_chunks=[
            {
                "text": "Attention computes dot products.",
                "metadata": {"arxiv_id": "1706.03762"},
                "score": 0.9,
            }
        ],
        query="What is the attention mechanism?",
    )


def test_load_test_questions(tmp_path):
    questions = [
        {"id": "q01", "question": "Q?", "reference_answer": "A.", "category": "T", "papers": []}
    ]
    f = tmp_path / "test_questions.json"
    f.write_text(json.dumps(questions), encoding="utf-8")

    from evaluation.eval import load_test_questions

    result = load_test_questions(f)
    assert len(result) == 1
    assert result[0]["id"] == "q01"


def test_load_all_25_questions():
    from evaluation.eval import load_test_questions

    questions = load_test_questions()
    assert len(questions) == 25


def test_load_questions_required_fields():
    from evaluation.eval import load_test_questions

    questions = load_test_questions()
    for q in questions:
        assert "id" in q
        assert "question" in q
        assert "reference_answer" in q
        assert "category" in q


def test_build_evaluation_dataset_structure(sample_questions, mock_rag_response, settings):
    with patch("evaluation.eval.ask", return_value=mock_rag_response):
        from evaluation.eval import build_evaluation_dataset

        dataset, raw_results = build_evaluation_dataset(sample_questions, settings)

    assert len(raw_results) == 2
    for r in raw_results:
        assert "id" in r
        assert "question" in r
        assert "answer" in r
        assert "sources" in r


def test_build_evaluation_dataset_fields(sample_questions, mock_rag_response, settings):
    with patch("evaluation.eval.ask", return_value=mock_rag_response):
        from evaluation.eval import build_evaluation_dataset

        dataset, _ = build_evaluation_dataset(sample_questions, settings)

    assert len(dataset) == 2


def test_save_results_creates_files(tmp_path, settings):
    import pandas as pd

    from evaluation import eval as eval_module

    mock_results = MagicMock()
    mock_results.to_pandas.return_value = pd.DataFrame(
        [
            {"faithfulness": 0.9, "answer_relevancy": 0.85, "context_precision": 0.80},
            {"faithfulness": 0.88, "answer_relevancy": 0.82, "context_precision": 0.78},
        ]
    )

    raw_results = [
        {
            "id": "q01",
            "question": "Q1?",
            "category": "T",
            "answer": "A1",
            "sources": [],
        },
        {
            "id": "q02",
            "question": "Q2?",
            "category": "R",
            "answer": "A2",
            "sources": [],
        },
    ]

    original_scores = eval_module.SCORES_PATH
    original_report = eval_module.REPORT_PATH
    eval_module.SCORES_PATH = tmp_path / "ragas_scores.json"
    eval_module.REPORT_PATH = tmp_path / "ragas_report.md"

    try:
        aggregate = eval_module.save_results(mock_results, raw_results)
    finally:
        eval_module.SCORES_PATH = original_scores
        eval_module.REPORT_PATH = original_report

    assert (tmp_path / "ragas_scores.json").exists()
    assert (tmp_path / "ragas_report.md").exists()
    assert aggregate["faithfulness"] == pytest.approx(0.89, abs=0.01)


def test_questions_cover_all_categories():
    from evaluation.eval import load_test_questions

    questions = load_test_questions()
    categories = {q["category"] for q in questions}
    assert "Transformers" in categories
    assert "Retrieval" in categories
    assert "FineTuning" in categories
    assert "Prompting" in categories
    assert "Synthesis" in categories
