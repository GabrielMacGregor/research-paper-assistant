# Research — Phase 1: Project Setup & Data Pipeline

> Researched: 2026-05-19 | Status: Complete

## Package Versions (Pinned)

| Package | Version | Import |
|---|---|---|
| pymupdf | 1.27.2+ | `import pymupdf` (not `fitz`) |
| chromadb | 1.5.9+ | `from chromadb import PersistentClient` |
| langchain-huggingface | 1.2.1 | `from langchain_huggingface import HuggingFaceEmbeddings` |
| langchain-ollama | 1.1.0 | `from langchain_ollama import ChatOllama` |
| sentence-transformers | 5.5.0 | transitive dep of langchain-huggingface |
| pydantic | 2.x (< 2.13) | required by langchain + chromadb |
| pydantic-settings | 2.x | `from pydantic_settings import BaseSettings` |

## Key API Details

### PyMuPDF
- Import: `import pymupdf` (the old `import fitz` still works but is deprecated)
- Open: `doc = pymupdf.open(path)`
- Iterate pages: `for page in doc: text = page.get_text()`
- `get_text()` returns plain text; `get_text("blocks")` returns structured blocks
- Close: `doc.close()`

### ChromaDB
- `PersistentClient(path="data/chroma_db")` — stores data to disk
- `client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})` — idempotent
- `collection.add(embeddings, documents, metadatas, ids)` — all lists
- `collection.count()` — returns total items
- `collection.get(ids=[...])` — fetch by ID (use for deduplication)
- **Gotcha**: Do NOT use `chromadb.Client()` (deprecated); always use `PersistentClient`

### HuggingFaceEmbeddings
- `HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5", model_kwargs={"device": "cuda"}, encode_kwargs={"normalize_embeddings": True})`
- `embedder.embed_documents(["text1", "text2"])` → `list[list[float]]`
- `embedder.embed_query("question")` → `list[float]`
- First call downloads model (~130MB) to `~/.cache/huggingface/`
- `normalize_embeddings=True` is important for cosine similarity

### LangChain TextSplitter
- `from langchain_text_splitters import RecursiveCharacterTextSplitter`
- Note: package is `langchain-text-splitters` (separate from `langchain`)
- `RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)`
- `.split_text(text)` → `list[str]`

### RAGAS with Ollama (Phase 3 preview)
- Configure via `LangchainLLMWrapper(ChatOllama(model="mistral:7b"))`
- Or use OpenAI-compatible endpoint: point `openai` client to `http://localhost:11434/v1` with `api_key="ollama"`
- RAGAS metrics need a capable LLM — `mistral:7b` works but quality of judge matters

## Constraints & Gotchas

1. **Python 3.11** — do NOT use 3.14+, chromadb has Pydantic v2.12+ compatibility issues on 3.14
2. **pydantic < 2.13** — pin `pydantic>=2.0,<2.13` to be safe with chromadb 1.5.9
3. **ChatOllama, not OllamaLLM** — `OllamaLLM` is for legacy completion models; use `ChatOllama` for Mistral 7B / Llama 3.x
4. **HuggingFace model download** — first run downloads ~130MB; subsequent runs use cache
5. **ChromaDB deduplication** — check existing IDs before `collection.add()` to ensure idempotency
6. **Batch size for embeddings** — embed in batches of 64 to avoid OOM; BAAI/bge-small fits in 4GB VRAM

## arXiv Paper IDs (Verified)

All 25 papers accessible via `https://arxiv.org/pdf/{id}.pdf`:

```
1706.03762  Attention Is All You Need (2017)
1810.04805  BERT (2018)
1910.10683  T5 — Exploring the Limits of Transfer Learning (2019)
2005.14165  GPT-3 — Language Models are Few-Shot Learners (2020)
2005.11401  RAG — Retrieval-Augmented Generation (2020)
2004.04906  DPR — Dense Passage Retrieval (2020)
2004.12832  ColBERT (2020)
1702.08734  FAISS — Billion-scale similarity search (2017)
2106.09685  LoRA (2021)
2103.00020  CLIP (2021)
2102.12092  DALL-E (2021)
2203.02155  InstructGPT (2022)
2201.11903  Chain-of-Thought Prompting (2022)
2210.03629  ReAct (2022)
2203.11171  Self-Consistency (2022)
2212.08073  Constitutional AI (2022)
2112.10752  Latent Diffusion Models / Stable Diffusion (2022)
2205.14135  FlashAttention (2022)
2302.13971  LLaMA (2023)
2307.09288  LLaMA 2 (2023)
2310.06825  Mistral 7B (2023)
2401.04088  Mixtral of Experts (2024)
2312.11805  Gemini (2023)
2303.08774  GPT-4 Technical Report (2023)
2305.13048  RWKV (2023)
```
