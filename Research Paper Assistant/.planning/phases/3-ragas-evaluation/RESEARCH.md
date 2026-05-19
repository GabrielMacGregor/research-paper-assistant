# Research — Phase 3: RAGAS Evaluation

> Researched: 2026-05-19 | Status: Complete

## RAGAS 0.2.x API (version ~0.2.15)

### LLM + Embeddings Configuration

```python
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper

evaluator_llm = LangchainLLMWrapper(
    ChatOllama(model="mistral:7b", temperature=0)
)
embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
)
```

### Dataset Format

Use `EvaluationDataset` — NOT raw HuggingFace Dataset:

```python
from ragas import EvaluationDataset

dataset = EvaluationDataset.from_list([{
    "user_input": "What is RAG?",           # question
    "response": "RAG augments LLMs...",     # generated answer
    "retrieved_contexts": ["chunk1", "chunk2"],  # list of strings (NOT list of lists)
    "reference": "RAG is Retrieval-Augmented Generation"  # ground truth
}])
```

Fields: `user_input`, `response`, `retrieved_contexts` (list[str]), `reference`.

### Metrics

```python
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision

metrics = [
    Faithfulness(llm=evaluator_llm),
    AnswerRelevancy(llm=evaluator_llm, embeddings=embeddings),
    ContextPrecision(llm=evaluator_llm),
]
```

All three metrics require LLM injection. `AnswerRelevancy` also needs embeddings.

### evaluate() Call

```python
from ragas import evaluate

results = evaluate(
    dataset=dataset,
    metrics=metrics,
    llm=evaluator_llm,
    embeddings=embeddings,
    show_progress=True,
)

df = results.to_pandas()     # per-question scores DataFrame
print(results)               # aggregate means printed directly
```

Returns `EvaluationResult`. Use `.to_pandas()` for per-question breakdown.

## Breaking Changes from 0.1.x → 0.2.x

| 0.1.x | 0.2.x |
|---|---|
| Raw dict / HuggingFace Dataset | `EvaluationDataset.from_list()` |
| `from ragas import faithfulness` (object) | `from ragas.metrics import Faithfulness` (class) |
| Metrics auto-initialize with OpenAI | Metrics require explicit `llm=` at init |
| `ascore()` | `single_turn_ascore()` (async) |
| `question` field | `user_input` field |
| `answer` field | `response` field |
| `contexts` field (list[list[str]]) | `retrieved_contexts` field (list[str]) |

## Performance Expectations

With `mistral:7b` locally on NVIDIA 4GB+ GPU:
- ~5-15s per question for pipeline (retrieve + generate)
- ~10-30s per question for RAGAS evaluation (LLM-as-judge calls)
- 25 questions total runtime: ~15-45 minutes

**Recommendation**: Support `--sample N` flag to evaluate a subset quickly during development.

## Gotchas

1. `retrieved_contexts` is `list[str]` — NOT `list[list[str]]` as in 0.1.x
2. Both `llm=` and `embeddings=` are required in the `evaluate()` call
3. RAGAS makes multiple LLM calls per question (faithfulness alone does ~3 calls)
4. Local LLMs may produce lower RAGAS scores than GPT-4 — the judge quality matters
5. If Ollama returns malformed JSON, RAGAS may fail silently — add error handling
