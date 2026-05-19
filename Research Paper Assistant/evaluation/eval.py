"""RAGAS evaluation for the Research Paper Assistant RAG pipeline."""

import argparse
import json
import logging
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, ContextPrecision, Faithfulness

from config.settings import Settings
from src.pipeline import ask

logger = logging.getLogger(__name__)

TEST_QUESTIONS_PATH = Path("evaluation/test_questions.json")
RESULTS_DIR = Path("evaluation/results")
SCORES_PATH = RESULTS_DIR / "ragas_scores.json"
REPORT_PATH = RESULTS_DIR / "ragas_report.md"

THRESHOLDS = {
    "faithfulness": 0.85,
    "answer_relevancy": 0.80,
    "context_precision": 0.75,
}


def load_test_questions(path: Path = TEST_QUESTIONS_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_evaluation_dataset(
    questions: list[dict],
    settings: Settings,
) -> tuple[EvaluationDataset, list[dict]]:
    """Run the RAG pipeline on each question and collect answers + contexts."""
    rows = []
    raw_results = []

    for i, q in enumerate(questions, start=1):
        logger.info("[%d/%d] %s", i, len(questions), q["question"][:70])
        response = ask(q["question"], settings)

        rows.append({
            "user_input": q["question"],
            "response": response.answer,
            "retrieved_contexts": [c["text"] for c in response.context_chunks],
            "reference": q["reference_answer"],
        })
        raw_results.append({
            "id": q["id"],
            "question": q["question"],
            "category": q["category"],
            "answer": response.answer,
            "sources": [
                {"title": s.title, "year": s.year, "arxiv_id": s.arxiv_id}
                for s in response.sources
            ],
        })

    return EvaluationDataset.from_list(rows), raw_results


def run_ragas(dataset: EvaluationDataset, settings: Settings):
    """Configure local Ollama judge + HuggingFace embeddings and run RAGAS."""
    evaluator_llm = LangchainLLMWrapper(
        ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
    )
    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": settings.embedding_device},
            encode_kwargs={"normalize_embeddings": True},
        )
    )

    metrics = [
        Faithfulness(llm=evaluator_llm),
        AnswerRelevancy(llm=evaluator_llm, embeddings=embeddings),
        ContextPrecision(llm=evaluator_llm),
    ]

    return evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=embeddings,
        show_progress=True,
    )


def save_results(results, raw_results: list[dict]) -> dict:
    """Persist ragas_scores.json and ragas_report.md."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    df = results.to_pandas()
    aggregate = {
        "faithfulness": round(float(df["faithfulness"].mean()), 4),
        "answer_relevancy": round(float(df["answer_relevancy"].mean()), 4),
        "context_precision": round(float(df["context_precision"].mean()), 4),
        "n_questions": len(df),
    }

    per_question = []
    for row_result, raw in zip(df.to_dict("records"), raw_results):
        per_question.append({
            **raw,
            "scores": {
                "faithfulness": round(row_result.get("faithfulness") or 0.0, 4),
                "answer_relevancy": round(row_result.get("answer_relevancy") or 0.0, 4),
                "context_precision": round(row_result.get("context_precision") or 0.0, 4),
            },
        })

    output = {"aggregate": aggregate, "per_question": per_question}
    with open(SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    _write_report(aggregate, per_question)
    return aggregate


def _write_report(aggregate: dict, per_question: list[dict]) -> None:
    def badge(metric: str, score: float) -> str:
        return "PASS" if score >= THRESHOLDS[metric] else "FAIL"

    lines = [
        "# RAGAS Evaluation Report — Research Paper Assistant",
        "",
        f"> n={aggregate['n_questions']} questions | LLM judge: Ollama (local) | Embeddings: BAAI/bge-small-en-v1.5",
        "",
        "## Aggregate Scores",
        "",
        "| Metric | Score | Threshold | Status |",
        "|---|---|---|---|",
        f"| Faithfulness | {aggregate['faithfulness']:.3f} | >= 0.85 | {badge('faithfulness', aggregate['faithfulness'])} |",
        f"| Answer Relevancy | {aggregate['answer_relevancy']:.3f} | >= 0.80 | {badge('answer_relevancy', aggregate['answer_relevancy'])} |",
        f"| Context Precision | {aggregate['context_precision']:.3f} | >= 0.75 | {badge('context_precision', aggregate['context_precision'])} |",
        "",
        "## Per-Question Breakdown",
        "",
        "| ID | Category | Question | Faith. | Rel. | Prec. |",
        "|---|---|---|---|---|---|",
    ]

    for q in per_question:
        s = q["scores"]
        short_q = q["question"][:55] + ("..." if len(q["question"]) > 55 else "")
        lines.append(
            f"| {q['id']} | {q['category']} | {short_q} "
            f"| {s['faithfulness']:.2f} | {s['answer_relevancy']:.2f} | {s['context_precision']:.2f} |"
        )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written to %s", REPORT_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on the RAG pipeline.")
    parser.add_argument(
        "--sample", type=int, default=None,
        help="Evaluate only the first N questions (for quick dev runs)",
    )
    args = parser.parse_args()

    settings = Settings()
    questions = load_test_questions()

    if args.sample:
        questions = questions[: args.sample]
        logger.info("Sampling %d / 25 questions", args.sample)

    logger.info("Step 1/2: Generating RAG answers for %d questions...", len(questions))
    dataset, raw_results = build_evaluation_dataset(questions, settings)

    logger.info("Step 2/2: Running RAGAS evaluation (this may take 15-45 min)...")
    results = run_ragas(dataset, settings)

    aggregate = save_results(results, raw_results)

    print("\n" + "=" * 55)
    print("RAGAS Evaluation Complete")
    print("=" * 55)
    for metric, score in aggregate.items():
        if metric == "n_questions":
            continue
        threshold = THRESHOLDS[metric]
        status = "PASS" if score >= threshold else "FAIL"
        print(f"  {metric:<22} {score:.3f}  (>= {threshold})  [{status}]")
    print(f"\n  Questions evaluated: {aggregate['n_questions']}")
    print(f"  Report: {REPORT_PATH}")
    print(f"  JSON:   {SCORES_PATH}")
