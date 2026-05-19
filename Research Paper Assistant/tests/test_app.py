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
