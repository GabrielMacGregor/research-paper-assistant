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
