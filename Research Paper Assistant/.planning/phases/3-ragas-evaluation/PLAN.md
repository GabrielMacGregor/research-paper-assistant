# Phase 3 Plan — RAGAS Evaluation

> Phase: 3 | Status: ready | Created: 2026-05-19 | Depends on: Phase 2

## Goal

Build a quantitative evaluation pipeline using RAGAS: 25 curated Q&A pairs → RAG pipeline answers → RAGAS judge (faithfulness, answer_relevancy, context_precision) → JSON scores + Markdown report.

## Pre-conditions

- Phase 2 complete: `python src/pipeline.py --query "..."` works
- Ollama running with `mistral:7b` pulled
- ChromaDB populated (Phase 1 pipeline executed)
- `make install` run

## Architecture

```
evaluation/test_questions.json  (25 Q&A pairs with reference answers)
         │
         ▼
evaluation/eval.py
  1. For each question → src/pipeline.ask() → answer + context_chunks
  2. Build EvaluationDataset (user_input, response, retrieved_contexts, reference)
  3. LangchainLLMWrapper(ChatOllama) + LangchainEmbeddingsWrapper(HuggingFaceEmbeddings)
  4. ragas.evaluate(dataset, [Faithfulness, AnswerRelevancy, ContextPrecision])
  5. results.to_pandas() → per-question scores
         │
         ▼
evaluation/results/ragas_scores.json   — full output (gitignored)
evaluation/results/ragas_report.md     — human-readable report (committed)
```

## Execution Waves

---

### Wave 1 — Test questions dataset + scaffolding (run in parallel)

#### Task 1.1 — Create `evaluation/__init__.py` and results directory

```bash
touch evaluation/__init__.py
mkdir -p evaluation/results
touch evaluation/results/.gitkeep
```

#### Task 1.2 — Create `evaluation/test_questions.json`

25 questions across 5 categories. Each entry has:
- `id`: q01–q25
- `question`: the query sent to the RAG pipeline
- `reference_answer`: ground-truth answer for RAGAS judge
- `category`: one of Transformers | Retrieval | FineTuning | Prompting | Synthesis
- `papers`: list of relevant arXiv IDs from the corpus

```json
[
  {
    "id": "q01",
    "question": "What is the attention mechanism in the Transformer model?",
    "reference_answer": "The attention mechanism computes a weighted sum of value vectors, where the weights are determined by the compatibility of a query vector with key vectors. Scaled dot-product attention computes Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) * V, where Q, K, V are matrices of queries, keys, and values projected from the input.",
    "category": "Transformers",
    "papers": ["1706.03762"]
  },
  {
    "id": "q02",
    "question": "What is multi-head attention and why is it useful?",
    "reference_answer": "Multi-head attention runs multiple attention functions in parallel (h heads), each with different learned linear projections of Q, K, V, then concatenates and projects the results. It allows the model to jointly attend to information from different representation subspaces at different positions, capturing diverse aspects of relationships between tokens.",
    "category": "Transformers",
    "papers": ["1706.03762"]
  },
  {
    "id": "q03",
    "question": "What are the roles of Query, Key, and Value in the attention function?",
    "reference_answer": "In attention, the Query (Q) represents the current position seeking information. The Key (K) represents positions being compared against the query for relevance scoring. The Value (V) holds the content to be retrieved. Attention scores are computed from Query-Key compatibility via dot product, and these scores weight the Values to produce the output.",
    "category": "Transformers",
    "papers": ["1706.03762"]
  },
  {
    "id": "q04",
    "question": "What is the difference between the encoder and decoder in the Transformer?",
    "reference_answer": "The encoder maps an input sequence to continuous representations using self-attention and feed-forward layers. The decoder generates output one token at a time using masked self-attention (preventing future positions from being attended to), plus cross-attention to the encoder outputs. The masking ensures autoregressive generation.",
    "category": "Transformers",
    "papers": ["1706.03762"]
  },
  {
    "id": "q05",
    "question": "What is positional encoding in the Transformer and why is it needed?",
    "reference_answer": "Positional encoding adds position information to token embeddings since the Transformer has no recurrence or convolution and is order-invariant. Vaswani et al. use sine and cosine functions of different frequencies: PE(pos,2i) = sin(pos/10000^(2i/d_model)) and PE(pos,2i+1) = cos(pos/10000^(2i/d_model)), allowing the model to learn to attend by relative positions.",
    "category": "Transformers",
    "papers": ["1706.03762"]
  },
  {
    "id": "q06",
    "question": "What is Retrieval-Augmented Generation (RAG) and how does it work?",
    "reference_answer": "RAG (Lewis et al., 2020) combines a parametric memory (pre-trained seq2seq model, BART) with a non-parametric memory (dense vector index of Wikipedia passages via DPR). For each input, RAG retrieves the top-k relevant passages using DPR, then conditions the BART generator on both the input and retrieved passages to produce grounded outputs.",
    "category": "Retrieval",
    "papers": ["2005.11401"]
  },
  {
    "id": "q07",
    "question": "What is Dense Passage Retrieval (DPR) and how does it differ from sparse retrieval?",
    "reference_answer": "DPR (Karpukhin et al., 2020) uses a BERT-based dual encoder to represent questions and passages as dense vectors, retrieving by maximum inner product search. Unlike sparse retrieval (TF-IDF, BM25) which relies on exact term overlap, DPR learns semantic representations enabling retrieval of relevant passages even without exact keyword matches.",
    "category": "Retrieval",
    "papers": ["2004.04906"]
  },
  {
    "id": "q08",
    "question": "What is ColBERT's late interaction approach to passage retrieval?",
    "reference_answer": "ColBERT (Khattab & Zaharia, 2020) independently encodes query and document tokens with BERT, then computes relevance via a MaxSim operator: for each query token embedding, it finds the maximum cosine similarity to any document token embedding, and sums these per-query-token scores. This enables expressive token-level interaction while pre-computing document representations offline for efficiency.",
    "category": "Retrieval",
    "papers": ["2004.12832"]
  },
  {
    "id": "q09",
    "question": "How does FAISS enable billion-scale similarity search?",
    "reference_answer": "FAISS (Johnson et al., 2017) uses GPU-optimized algorithms including product quantization for vector compression, inverted file (IVF) structures for candidate selection, and optimized matrix multiplication for inner product computation. It supports both exact and approximate nearest-neighbor search in high-dimensional spaces, scaling to billions of vectors by leveraging GPU parallelism.",
    "category": "Retrieval",
    "papers": ["1702.08734"]
  },
  {
    "id": "q10",
    "question": "What are the main components of a RAG system according to Lewis et al.?",
    "reference_answer": "According to Lewis et al. (2020), a RAG system consists of: (1) a retriever (DPR dual encoder) that encodes queries and documents into dense vectors and retrieves top-k relevant passages via MIPS, (2) a generator (BART seq2seq model) that conditions on the concatenation of input and retrieved passages to generate the answer, and (3) a pre-indexed document corpus.",
    "category": "Retrieval",
    "papers": ["2005.11401", "2004.04906"]
  },
  {
    "id": "q11",
    "question": "What is LoRA and how does it reduce the number of trainable parameters?",
    "reference_answer": "LoRA (Hu et al., 2021) freezes pre-trained model weights and injects trainable low-rank decomposition matrices into Transformer layers. For a weight matrix W ∈ R^(d×k), the update ΔW = BA where B ∈ R^(d×r) and A ∈ R^(r×k) with rank r << min(d,k). For GPT-3 175B with r=4, this reduces trainable parameters by 10,000x while maintaining comparable performance to full fine-tuning.",
    "category": "FineTuning",
    "papers": ["2106.09685"]
  },
  {
    "id": "q12",
    "question": "What is the key hypothesis behind LoRA's low-rank adaptation?",
    "reference_answer": "The key hypothesis in LoRA (Hu et al., 2021) is that weight updates during fine-tuning have low intrinsic rank — the changes to pre-trained weights necessary for downstream tasks lie in a low-dimensional subspace. The authors support this with empirical evidence showing that pre-trained models have low intrinsic dimensionality, meaning tasks can be learned by updating only a small rank subspace.",
    "category": "FineTuning",
    "papers": ["2106.09685"]
  },
  {
    "id": "q13",
    "question": "What is RLHF and what are the three steps used in InstructGPT?",
    "reference_answer": "RLHF (Reinforcement Learning from Human Feedback) aligns language models to human intent. InstructGPT (Ouyang et al., 2022) uses three steps: (1) supervised fine-tuning on human-written demonstrations, (2) reward model training from human comparisons between model outputs, and (3) PPO optimization of the policy against the reward model with a KL penalty to prevent deviation from the SFT model.",
    "category": "FineTuning",
    "papers": ["2203.02155"]
  },
  {
    "id": "q14",
    "question": "What is Constitutional AI and how does it reduce reliance on human labels?",
    "reference_answer": "Constitutional AI (Bai et al., 2022) uses a set of principles (a 'constitution') to guide AI self-improvement without needing human labels for harmful outputs. In the supervised phase, the model critiques and revises its own outputs according to the principles. In the RL phase, AI-generated preference labels (from a feedback model) replace human annotations, reducing the need for humans to evaluate harmful content.",
    "category": "FineTuning",
    "papers": ["2212.08073"]
  },
  {
    "id": "q15",
    "question": "How does BERT's pre-training differ from GPT's pre-training approach?",
    "reference_answer": "BERT (Devlin et al., 2018) uses bidirectional pre-training: masked language modeling (MLM), where 15% of tokens are masked and predicted using context from both directions, plus next sentence prediction. GPT uses unidirectional (left-to-right) autoregressive language modeling, predicting each token from only the left context. BERT's bidirectionality makes it better for understanding tasks, while GPT's autoregressive training suits generation.",
    "category": "FineTuning",
    "papers": ["1810.04805"]
  },
  {
    "id": "q16",
    "question": "What is chain-of-thought prompting and why does it improve reasoning in LLMs?",
    "reference_answer": "Chain-of-thought prompting (Wei et al., 2022) provides LLMs with exemplars that include intermediate reasoning steps before the final answer. It improves performance on arithmetic, commonsense, and symbolic reasoning tasks by encouraging step-by-step problem decomposition. The improvement is an emergent capability that appears in sufficiently large models (~100B+ parameters).",
    "category": "Prompting",
    "papers": ["2201.11903"]
  },
  {
    "id": "q17",
    "question": "What is the ReAct framework and how does it combine reasoning with action?",
    "reference_answer": "ReAct (Yao et al., 2022) interleaves reasoning traces (Thought) with task-specific actions (Act) and observations (Obs) in language model prompts. Thoughts plan what action to take and update understanding based on observations. Actions interact with external tools (e.g., Wikipedia search). This tight loop between reasoning and grounded action enables more accurate and interpretable problem-solving.",
    "category": "Prompting",
    "papers": ["2210.03629"]
  },
  {
    "id": "q18",
    "question": "What is self-consistency and how does it improve chain-of-thought prompting?",
    "reference_answer": "Self-consistency (Wang et al., 2022) replaces greedy decoding in chain-of-thought with sampling multiple diverse reasoning paths, then taking a majority vote on the final answers. The intuition is that correct answers are reached by multiple valid reasoning paths while incorrect answers tend to be inconsistent. Self-consistency improves accuracy on arithmetic and commonsense tasks without requiring additional training.",
    "category": "Prompting",
    "papers": ["2203.11171"]
  },
  {
    "id": "q19",
    "question": "What is in-context few-shot learning and how does GPT-3 demonstrate it?",
    "reference_answer": "Few-shot in-context learning allows a model to perform tasks given only a few examples in the prompt, without gradient updates. GPT-3 (Brown et al., 2020) demonstrates that a 175B parameter language model can achieve competitive performance on many benchmarks using only K demonstration examples (typically K=1-32) in the context, without any fine-tuning, by learning task format from examples alone.",
    "category": "Prompting",
    "papers": ["2005.14165"]
  },
  {
    "id": "q20",
    "question": "What is the difference between zero-shot and few-shot prompting in GPT-3?",
    "reference_answer": "In zero-shot prompting, the model receives only a task description and input with no examples. In few-shot prompting, K example input-output pairs are prepended to the prompt to show the model the expected format and task behavior. GPT-3 (Brown et al., 2020) shows that few-shot consistently outperforms zero-shot, but both benefit from scale, suggesting emergent in-context learning from pre-training.",
    "category": "Prompting",
    "papers": ["2005.14165"]
  },
  {
    "id": "q21",
    "question": "How did the Transformer architecture enable the development of BERT and GPT-3?",
    "reference_answer": "The Transformer (Vaswani et al., 2017) provided a scalable, parallelizable architecture using self-attention, replacing sequential RNNs. BERT (Devlin et al., 2018) adopted the Transformer encoder for bidirectional pre-training at scale, while GPT-3 (Brown et al., 2020) scaled the Transformer decoder to 175B parameters with autoregressive pre-training. Both showed that scaling Transformer-based pre-training yields powerful general-purpose representations.",
    "category": "Synthesis",
    "papers": ["1706.03762", "1810.04805", "2005.14165"]
  },
  {
    "id": "q22",
    "question": "What is the relationship between embedding alignment in CLIP and dense retrieval in DPR?",
    "reference_answer": "Both CLIP (Radford et al., 2021) and DPR (Karpukhin et al., 2020) use dual encoders to create aligned embedding spaces where similarity measures semantic relevance. CLIP aligns image and text embeddings for zero-shot classification. DPR aligns question and passage embeddings for retrieval. In both cases, contrastive learning trains encoders so that relevant pairs have high dot-product similarity, enabling efficient nearest-neighbor search.",
    "category": "Synthesis",
    "papers": ["2103.00020", "2004.04906"]
  },
  {
    "id": "q23",
    "question": "How does Mistral 7B achieve strong performance with only 7 billion parameters?",
    "reference_answer": "Mistral 7B (Jiang et al., 2023) outperforms larger models through architectural innovations: grouped-query attention (GQA) reduces memory bandwidth during inference, and sliding window attention (SWA) with a rolling buffer enables handling long sequences efficiently. The model uses a context window of 8192 tokens. These efficiency improvements allow Mistral 7B to outperform LLaMA 2 13B on most benchmarks despite having fewer parameters.",
    "category": "Synthesis",
    "papers": ["2310.06825"]
  },
  {
    "id": "q24",
    "question": "How does ReAct build on chain-of-thought prompting?",
    "reference_answer": "ReAct (Yao et al., 2022) directly extends chain-of-thought prompting (Wei et al., 2022). While CoT generates multi-step reasoning chains to reach an answer, ReAct adds an action dimension: after each reasoning step (Thought), the model can take an external action (Act) and observe results (Obs), which inform subsequent thoughts. This grounds the reasoning in real retrieved information, reducing hallucination compared to pure CoT.",
    "category": "Synthesis",
    "papers": ["2210.03629", "2201.11903"]
  },
  {
    "id": "q25",
    "question": "How does the attention mechanism in Transformers conceptually relate to retrieval in RAG systems?",
    "reference_answer": "Both Transformer attention (Vaswani et al., 2017) and RAG retrieval (Lewis et al., 2020) perform weighted information retrieval using Query-Key similarity. In Transformers, attention computes Query-Key dot products to weight Value vectors within the input sequence. In RAG, the retriever computes query-passage similarities (via DPR dense embeddings) to retrieve relevant documents from an external corpus. RAG can be seen as extending attention to a non-parametric external memory.",
    "category": "Synthesis",
    "papers": ["1706.03762", "2005.11401"]
  }
]
```

---

### Wave 2 — Evaluation script

#### Task 2.1 — Create `evaluation/eval.py`

```python
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
            "sources": [{"title": s.title, "year": s.year, "arxiv_id": s.arxiv_id}
                        for s in response.sources],
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
        return "✅ PASS" if score >= THRESHOLDS[metric] else "❌ FAIL"

    lines = [
        "# RAGAS Evaluation Report — Research Paper Assistant",
        "",
        f"> n={aggregate['n_questions']} questions | LLM judge: Ollama (local) | Embeddings: BAAI/bge-small-en-v1.5",
        "",
        "## Aggregate Scores",
        "",
        "| Metric | Score | Threshold | Status |",
        "|---|---|---|---|",
        f"| Faithfulness | {aggregate['faithfulness']:.3f} | ≥ 0.85 | {badge('faithfulness', aggregate['faithfulness'])} |",
        f"| Answer Relevancy | {aggregate['answer_relevancy']:.3f} | ≥ 0.80 | {badge('answer_relevancy', aggregate['answer_relevancy'])} |",
        f"| Context Precision | {aggregate['context_precision']:.3f} | ≥ 0.75 | {badge('context_precision', aggregate['context_precision'])} |",
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
        help="Evaluate only the first N questions (for quick dev runs)"
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
        print(f"  {metric:<22} {score:.3f}  (≥ {threshold})  [{status}]")
    print(f"\n  Questions evaluated: {aggregate['n_questions']}")
    print(f"  Report: {REPORT_PATH}")
    print(f"  JSON:   {SCORES_PATH}")
```

---

### Wave 3 — Unit tests

#### Task 3.1 — Create `tests/test_evaluation.py`

```python
"""Unit tests for evaluation/eval.py — mocked RAGAS and pipeline."""

import json
from pathlib import Path
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
        sources=[Source(title="Attention Is All You Need", authors="Vaswani et al.", year=2017, arxiv_id="1706.03762")],
        context_chunks=[{"text": "Attention computes dot products.", "metadata": {"arxiv_id": "1706.03762"}, "score": 0.9}],
        query="What is the attention mechanism?",
    )


def test_load_test_questions(tmp_path):
    questions = [{"id": "q01", "question": "Q?", "reference_answer": "A.", "category": "T", "papers": []}]
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

    # EvaluationDataset should have correct number of rows
    assert len(dataset) == 2


def test_save_results_creates_files(tmp_path, sample_questions, settings):
    import pandas as pd
    from evaluation import eval as eval_module

    mock_results = MagicMock()
    mock_results.to_pandas.return_value = pd.DataFrame([
        {"faithfulness": 0.9, "answer_relevancy": 0.85, "context_precision": 0.80},
        {"faithfulness": 0.88, "answer_relevancy": 0.82, "context_precision": 0.78},
    ])

    raw_results = [
        {"id": "q01", "question": "Q1?", "category": "T", "answer": "A1", "sources": [],
         "scores": {"faithfulness": 0.9, "answer_relevancy": 0.85, "context_precision": 0.80}},
        {"id": "q02", "question": "Q2?", "category": "R", "answer": "A2", "sources": [],
         "scores": {"faithfulness": 0.88, "answer_relevancy": 0.82, "context_precision": 0.78}},
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
```

---

### Wave 4 — Tooling updates (run in parallel)

#### Task 4.1 — Update `.gitignore`

Add to `.gitignore`:
```
# Evaluation results (large, generated — report committed separately)
evaluation/results/ragas_scores.json
```

#### Task 4.2 — Update `Makefile`

Add `eval` and `eval-sample` targets:
```makefile
eval:
	python evaluation/eval.py

eval-sample:
	python evaluation/eval.py --sample 5
```

---

## Verification Steps

```bash
# 1. Run tests (all mocked — no Ollama needed)
pytest tests/ -v

# 2. Lint
ruff check src/ tests/ scripts/ evaluation/

# 3. Quick evaluation sanity check (5 questions, ~5-10 min)
# (requires Ollama + ChromaDB populated)
python evaluation/eval.py --sample 5

# 4. Full evaluation (25 questions, ~15-45 min)
python evaluation/eval.py
```

## UAT Checklist

- [ ] `pytest tests/` — all tests pass including `test_evaluation.py`
- [ ] `ruff check` — lint clean
- [ ] `evaluation/test_questions.json` — 25 questions across 5 categories
- [ ] `python evaluation/eval.py --sample 5` completes without error
- [ ] `evaluation/results/ragas_scores.json` contains `aggregate` + `per_question`
- [ ] `evaluation/results/ragas_report.md` contains score table
- [ ] `faithfulness` ≥ 0.85 in aggregate
- [ ] `answer_relevancy` ≥ 0.80 in aggregate
- [ ] `context_precision` ≥ 0.75 in aggregate

## Performance Note

Full 25-question evaluation with local `mistral:7b`:
- Pipeline step: ~5-15s/question → ~5 min total
- RAGAS evaluation: ~10-30s/question → ~15-40 min total
- Use `--sample 5` for quick dev iteration before running full eval

## Phase Complete Criteria

All UAT items checked + tests green + lint clean + `ragas_report.md` committed with actual scores.
Next: `/gsd:plan-phase 4` — Streamlit Interface.
