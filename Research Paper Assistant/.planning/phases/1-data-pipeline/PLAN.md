# Phase 1 Plan — Project Setup & Data Pipeline

> Phase: 1 | Status: ready | Created: 2026-05-19

## Goal

Bootstrap the full project structure and data pipeline: 25 arXiv PDFs downloaded, parsed, chunked, embedded with HuggingFace BAAI/bge-small-en-v1.5, and persisted to ChromaDB — all running locally, zero API cost.

## Pre-conditions

- Python 3.11 installed (`python --version` → 3.11.x)
- pip / venv available
- NVIDIA GPU with 4GB+ VRAM (for embedding speed)
- Internet connection (to download papers and HuggingFace model on first run)

## Execution Waves

---

### Wave 1 — Scaffolding (run tasks in parallel)

#### Task 1.1 — Create directory structure

Create the following directories and empty `__init__.py` files:

```
mkdir -p data/papers data/chroma_db src scripts tests config app evaluation
touch src/__init__.py tests/__init__.py config/__init__.py
```

Directory map:
```
research-paper-assistant/
├── data/
│   ├── papers/              # PDFs (gitignored)
│   └── papers_metadata.json
├── src/
│   ├── __init__.py
│   ├── ingestion.py
│   └── embeddings.py
├── scripts/
│   └── download_papers.py
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py
│   └── test_embeddings.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── app/               # (Phase 4)
├── evaluation/        # (Phase 3)
├── .env.example
├── .gitignore
├── Makefile
├── pyproject.toml
└── requirements.txt
```

#### Task 1.2 — Create `.gitignore`

```gitignore
# Environment
.env
*.env

# Data (large files — keep metadata, exclude PDFs and vector DB)
data/papers/
data/chroma_db/

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
dist/
build/
*.egg-info/

# Testing
.pytest_cache/
.coverage
htmlcov/

# HuggingFace model cache (optional — cache is reusable)
# ~/.cache/huggingface/

# OS
.DS_Store
Thumbs.db
```

#### Task 1.3 — Create `.env.example`

```dotenv
# === Ollama (local LLM — no API key needed) ===
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
# Alternative: OLLAMA_MODEL=llama3.1:8b

# === Embeddings (HuggingFace local — no API key needed) ===
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DEVICE=cuda
# Use cpu if no NVIDIA GPU: EMBEDDING_DEVICE=cpu

# === ChromaDB ===
CHROMA_PATH=data/chroma_db
CHROMA_COLLECTION=research_papers

# === Ingestion ===
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K=5
```

---

### Wave 2 — Dependencies

#### Task 2.1 — Create `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "research-paper-assistant"
version = "0.1.0"
description = "RAG application for AI/ML research papers"
requires-python = ">=3.11"
readme = "README.md"
license = { text = "MIT" }

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
strict = false

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

#### Task 2.2 — Create `requirements.txt`

```txt
# PDF parsing
pymupdf==1.27.2

# LangChain ecosystem
langchain==0.3.25
langchain-core==0.3.57
langchain-huggingface==1.2.1
langchain-ollama==1.1.0
langchain-text-splitters==0.3.8

# Embeddings
sentence-transformers==5.5.0

# Vector store
chromadb==1.5.9

# Config
pydantic>=2.0,<2.13
pydantic-settings==2.8.1
python-dotenv==1.1.0

# Utils
requests==2.32.3
tqdm==4.67.1

# RAGAS (Phase 3 — install now to avoid conflicts later)
ragas==0.2.15
openai==1.82.0

# Testing
pytest==8.3.5
pytest-cov==6.1.0

# Dev
ruff==0.11.10
```

---

### Wave 3 — Core config + metadata (run in parallel)

#### Task 3.1 — Create `config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b"

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cuda"

    # ChromaDB
    chroma_path: str = "data/chroma_db"
    chroma_collection: str = "research_papers"

    # Ingestion
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k: int = 5
```

#### Task 3.2 — Create `data/papers_metadata.json`

```json
[
  {
    "arxiv_id": "1706.03762",
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones", "Aidan N. Gomez", "Łukasz Kaiser", "Illia Polosukhin"],
    "year": 2017,
    "topic": "Transformers"
  },
  {
    "arxiv_id": "1810.04805",
    "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
    "year": 2018,
    "topic": "Language Models"
  },
  {
    "arxiv_id": "1910.10683",
    "title": "Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer",
    "authors": ["Colin Raffel", "Noam Shazeer", "Adam Roberts", "Katherine Lee", "Sharan Narang", "Michael Matena", "Yanqi Zhou", "Wei Li", "Peter J. Liu"],
    "year": 2019,
    "topic": "Language Models"
  },
  {
    "arxiv_id": "2005.14165",
    "title": "Language Models are Few-Shot Learners",
    "authors": ["Tom B. Brown", "Benjamin Mann", "Nick Ryder", "Melanie Subbiah", "Jared Kaplan", "Prafulla Dhariwal", "Arvind Neelakantan", "Pranav Shyam", "Girish Sastry", "Amanda Askell", "Sandhini Agarwal", "Ariel Herbert-Voss", "Gretchen Krueger", "Tom Henighan", "Rewon Child", "Aditya Ramesh", "Daniel M. Ziegler", "Jeffrey Wu", "Clemens Winter", "Christopher Hesse", "Mark Chen", "Eric Sigler", "Mateusz Litwin", "Scott Gray", "Benjamin Chess", "Jack Clark", "Christopher Berner", "Sam McCandlish", "Alec Radford", "Ilya Sutskever", "Dario Amodei"],
    "year": 2020,
    "topic": "Language Models"
  },
  {
    "arxiv_id": "2005.11401",
    "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
    "authors": ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus", "Fabio Petroni", "Vladimir Karpukhin", "Naman Goyal", "Heinrich Küttler", "Mike Lewis", "Wen-tau Yih", "Tim Rocktäschel", "Sebastian Riedel", "Douwe Kiela"],
    "year": 2020,
    "topic": "Retrieval"
  },
  {
    "arxiv_id": "2004.04906",
    "title": "Dense Passage Retrieval for Open-Domain Question Answering",
    "authors": ["Vladimir Karpukhin", "Barlas Oguz", "Sewon Min", "Patrick Lewis", "Ledell Wu", "Sergey Edunov", "Danqi Chen", "Wen-tau Yih"],
    "year": 2020,
    "topic": "Retrieval"
  },
  {
    "arxiv_id": "2004.12832",
    "title": "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT",
    "authors": ["Omar Khattab", "Matei Zaharia"],
    "year": 2020,
    "topic": "Retrieval"
  },
  {
    "arxiv_id": "1702.08734",
    "title": "Billion-scale similarity search with GPUs",
    "authors": ["Jeff Johnson", "Matthijs Douze", "Hervé Jégou"],
    "year": 2017,
    "topic": "Vector Search"
  },
  {
    "arxiv_id": "2106.09685",
    "title": "LoRA: Low-Rank Adaptation of Large Language Models",
    "authors": ["Edward J. Hu", "Yelong Shen", "Phillip Wallis", "Zeyuan Allen-Zhu", "Yuanzhi Li", "Shean Wang", "Lu Wang", "Weizhu Chen"],
    "year": 2021,
    "topic": "Fine-tuning"
  },
  {
    "arxiv_id": "2103.00020",
    "title": "Learning Transferable Visual Models From Natural Language Supervision",
    "authors": ["Alec Radford", "Jong Wook Kim", "Chris Hallacy", "Aditya Ramesh", "Gabriel Goh", "Sandhini Agarwal", "Girish Sastry", "Amanda Askell", "Pamela Mishkin", "Jack Clark", "Gretchen Krueger", "Ilya Sutskever"],
    "year": 2021,
    "topic": "Multimodal"
  },
  {
    "arxiv_id": "2102.12092",
    "title": "Zero-Shot Text-to-Image Generation",
    "authors": ["Aditya Ramesh", "Mikhail Pavlov", "Gabriel Goh", "Scott Gray", "Chelsea Voss", "Alec Radford", "Mark Chen", "Ilya Sutskever"],
    "year": 2021,
    "topic": "Generative"
  },
  {
    "arxiv_id": "2203.02155",
    "title": "Training language models to follow instructions with human feedback",
    "authors": ["Long Ouyang", "Jeff Wu", "Xu Jiang", "Diogo Almeida", "Carroll L. Wainwright", "Pamela Mishkin", "Chong Zhang", "Sandhini Agarwal", "Katarina Slama", "Alex Ray", "John Schulman", "Jacob Hilton", "Fraser Kelton", "Luke Miller", "Maddie Simens", "Amanda Askell", "Peter Welinder", "Paul Christiano", "Jan Leike", "Ryan Lowe"],
    "year": 2022,
    "topic": "RLHF"
  },
  {
    "arxiv_id": "2201.11903",
    "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
    "authors": ["Jason Wei", "Xuezhi Wang", "Dale Schuurmans", "Maarten Bosma", "Brian Ichter", "Fei Xia", "Ed Chi", "Quoc Le", "Denny Zhou"],
    "year": 2022,
    "topic": "Prompting"
  },
  {
    "arxiv_id": "2210.03629",
    "title": "ReAct: Synergizing Reasoning and Acting in Language Models",
    "authors": ["Shunyu Yao", "Jeffrey Zhao", "Dian Yu", "Nan Du", "Izhak Shafran", "Karthik Narasimhan", "Yuan Cao"],
    "year": 2022,
    "topic": "Agents"
  },
  {
    "arxiv_id": "2203.11171",
    "title": "Self-Consistency Improves Chain of Thought Reasoning in Language Models",
    "authors": ["Xuezhi Wang", "Jason Wei", "Dale Schuurmans", "Quoc Le", "Ed Chi", "Shafiq Jowaheer", "Denny Zhou"],
    "year": 2022,
    "topic": "Prompting"
  },
  {
    "arxiv_id": "2212.08073",
    "title": "Constitutional AI: Harmlessness from AI Feedback",
    "authors": ["Yuntao Bai", "Saurav Kadavath", "Sandipan Kundu", "Amanda Askell", "Jackson Kernion", "Andy Jones", "Anna Chen", "Anna Goldie", "Azalia Mirhoseini", "Cameron McKinnon", "Carol Chen", "Catherine Olsson", "Christopher Olah", "Danny Hernandez", "Dawn Drain", "Deep Ganguli", "Dustin Li", "Eli Tran-Johnson", "Ethan Perez", "Jamie Kerr", "Jared Mueller", "Jeffrey Ladish", "Joshua Landau", "Kamal Ndousse", "Kamile Lukosuite", "Liane Lovitt", "Michael Sellitto", "Nelson Elhage", "Nicholas Schiefer", "Noemi Mercado", "Nova DasSarma", "Robert Lasenby", "Robin Larson", "Sam Ringer", "Scott Johnston", "Shauna Kravec", "Sheer El Showk", "Stanislav Fort", "Tamera Lanham", "Timothy Telleen-Lawton", "Tom Conerly", "Tom Henighan", "Tristan Hume", "Samuel R. Bowman", "Zac Hatfield-Dodds", "Ben Mann", "Dario Amodei", "Nicholas Joseph", "Sam McCandlish", "Tom Brown", "Jared Kaplan"],
    "year": 2022,
    "topic": "Safety"
  },
  {
    "arxiv_id": "2112.10752",
    "title": "High-Resolution Image Synthesis with Latent Diffusion Models",
    "authors": ["Robin Rombach", "Andreas Blattmann", "Dominik Lorenz", "Patrick Esser", "Björn Ommer"],
    "year": 2022,
    "topic": "Generative"
  },
  {
    "arxiv_id": "2205.14135",
    "title": "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness",
    "authors": ["Tri Dao", "Daniel Y. Fu", "Stefano Ermon", "Atri Rudra", "Christopher Ré"],
    "year": 2022,
    "topic": "Efficiency"
  },
  {
    "arxiv_id": "2302.13971",
    "title": "LLaMA: Open and Efficient Foundation Language Models",
    "authors": ["Hugo Touvron", "Thibaut Lavril", "Gautier Izacard", "Xavier Martinet", "Marie-Anne Lachaux", "Timothée Lacroix", "Baptiste Rozière", "Naman Goyal", "Eric Hambro", "Faisal Azhar", "Aurelien Rodriguez", "Armand Joulin", "Edouard Grave", "Guillaume Lample"],
    "year": 2023,
    "topic": "Open Models"
  },
  {
    "arxiv_id": "2307.09288",
    "title": "Llama 2: Open Foundation and Fine-Tuned Chat Models",
    "authors": ["Hugo Touvron", "Louis Martin", "Kevin Stone", "Peter Albert", "Amjad Almahairi", "Yasmine Babaei", "Nikolay Bashlykov", "Soumya Batra", "Prajjwal Bhargava", "Shruti Bhosale"],
    "year": 2023,
    "topic": "Open Models"
  },
  {
    "arxiv_id": "2310.06825",
    "title": "Mistral 7B",
    "authors": ["Albert Q. Jiang", "Alexandre Sablayrolles", "Arthur Mensch", "Chris Bamford", "Devendra Singh Chaplot", "Diego de las Casas", "Florian Bressand", "Gianna Lengyel", "Guillaume Lample", "Lucile Saulnier", "Lélio Renard Lavaud", "Marie-Anne Lachaux", "Pierre Stock", "Teven Le Scao", "Thibaut Lavril", "Thomas Wang", "Timothée Lacroix", "William El Sayed"],
    "year": 2023,
    "topic": "Open Models"
  },
  {
    "arxiv_id": "2401.04088",
    "title": "Mixtral of Experts",
    "authors": ["Albert Q. Jiang", "Alexandre Sablayrolles", "Antoine Roux", "Arthur Mensch", "Blanche Savary", "Chris Bamford", "Devendra Singh Chaplot", "Diego de las Casas", "Emma Bou Hanna", "Florian Bressand", "Gianna Lengyel", "Guillaume Bour", "Guillaume Lample", "Lélio Renard Lavaud", "Lucile Saulnier", "Marie-Anne Lachaux", "Pierre Stock", "Sandeep Subramanian", "Sophia Yang", "Szymon Antoniak", "Teven Le Scao", "Théophile Gervet", "Thibaut Lavril", "Thomas Wang", "Timothée Lacroix", "William El Sayed"],
    "year": 2024,
    "topic": "MoE"
  },
  {
    "arxiv_id": "2312.11805",
    "title": "Gemini: A Family of Highly Capable Multimodal Models",
    "authors": ["Gemini Team", "Google"],
    "year": 2023,
    "topic": "Multimodal"
  },
  {
    "arxiv_id": "2303.08774",
    "title": "GPT-4 Technical Report",
    "authors": ["OpenAI"],
    "year": 2023,
    "topic": "Language Models"
  },
  {
    "arxiv_id": "2305.13048",
    "title": "RWKV: Reinventing RNNs for the Transformer Era",
    "authors": ["Bo Peng", "Eric Alcaide", "Quentin Anthony", "Alon Albalak", "Samuel Arcadinho", "Huanqi Cao", "Xin Cheng", "Michael Chung", "Matteo Grella", "Kranthi Kiran GV", "Xuzheng He", "Haowen Hou", "Przemyslaw Kazienko", "Jan Kocon", "Jiaming Kong", "Bartlomiej Koptyra", "Hayden Lau", "Krishna Sri Ipsit Mantri", "Ferdinand Mom", "Atsushi Saito", "Xiangru Tang", "Bolun Wang", "Johan S. Wind", "Stansilaw Wozniak", "Ruichong Zhang", "Zhenyuan Zhang", "Qihang Zhao", "Peng Zhou", "Jian Zhu", "Rui-Jie Zhu"],
    "year": 2023,
    "topic": "Architecture"
  }
]
```

---

### Wave 4 — Source files (run in parallel)

#### Task 4.1 — Create `scripts/download_papers.py`

```python
"""Download arXiv papers as PDFs to data/papers/."""

import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

PAPERS_METADATA_PATH = Path("data/papers_metadata.json")
OUTPUT_DIR = Path("data/papers")
ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
RATE_LIMIT_SECONDS = 3


def download_paper(arxiv_id: str, output_dir: Path) -> Path | None:
    output_path = output_dir / f"{arxiv_id}.pdf"
    if output_path.exists() and output_path.stat().st_size > 1000:
        return output_path

    url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    try:
        response = requests.get(url, stream=True, timeout=60, headers={"User-Agent": "RAG-Research-Assistant/1.0"})
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_path
    except requests.RequestException as e:
        print(f"  ERROR downloading {arxiv_id}: {e}")
        return None


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PAPERS_METADATA_PATH) as f:
        papers = json.load(f)

    print(f"Downloading {len(papers)} papers to {OUTPUT_DIR}/")
    success, failed = 0, []

    for paper in tqdm(papers, desc="Downloading"):
        arxiv_id = paper["arxiv_id"]
        result = download_paper(arxiv_id, OUTPUT_DIR)
        if result:
            success += 1
        else:
            failed.append(arxiv_id)
        time.sleep(RATE_LIMIT_SECONDS)  # be polite to arXiv

    print(f"\nDone: {success}/{len(papers)} downloaded")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
```

#### Task 4.2 — Create `src/ingestion.py`

```python
"""PDF ingestion: parse with PyMuPDF, chunk with LangChain RecursiveCharacterTextSplitter."""

import json
import logging
from pathlib import Path

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import Settings

logger = logging.getLogger(__name__)


def load_metadata(metadata_path: Path = Path("data/papers_metadata.json")) -> dict[str, dict]:
    with open(metadata_path) as f:
        papers = json.load(f)
    return {p["arxiv_id"]: p for p in papers}


def extract_pages(pdf_path: Path) -> list[dict]:
    """Extract text page-by-page. Returns list of {page: int, text: str}."""
    doc = pymupdf.open(str(pdf_path))
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text.strip():
            pages.append({"page": page_num, "text": text})
    doc.close()
    return pages


def chunk_pages(
    pages: list[dict],
    paper_metadata: dict,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[dict]:
    """Split page texts into overlapping chunks, attaching paper metadata to each."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks: list[dict] = []
    chunk_index = 0
    base_meta = {
        "paper_id": paper_metadata["arxiv_id"],
        "title": paper_metadata["title"],
        "authors": ", ".join(paper_metadata["authors"][:3])
            + (" et al." if len(paper_metadata["authors"]) > 3 else ""),
        "year": paper_metadata["year"],
        "arxiv_id": paper_metadata["arxiv_id"],
        "topic": paper_metadata.get("topic", ""),
    }
    for page_info in pages:
        for text in splitter.split_text(page_info["text"]):
            if text.strip():
                chunks.append({
                    "text": text,
                    "metadata": {**base_meta, "page": page_info["page"], "chunk_index": chunk_index},
                })
                chunk_index += 1
    return chunks


def ingest_paper(pdf_path: Path, paper_metadata: dict, settings: Settings) -> list[dict]:
    pages = extract_pages(pdf_path)
    return chunk_pages(pages, paper_metadata, settings.chunk_size, settings.chunk_overlap)


def ingest_all(settings: Settings | None = None) -> list[dict]:
    if settings is None:
        settings = Settings()

    papers_dir = Path("data/papers")
    metadata_by_id = load_metadata()
    all_chunks: list[dict] = []

    for pdf_path in sorted(papers_dir.glob("*.pdf")):
        arxiv_id = pdf_path.stem
        if arxiv_id not in metadata_by_id:
            logger.warning("No metadata found for %s — skipping", arxiv_id)
            continue
        paper_meta = metadata_by_id[arxiv_id]
        logger.info("Ingesting %s: %s", arxiv_id, paper_meta["title"])
        chunks = ingest_paper(pdf_path, paper_meta, settings)
        all_chunks.extend(chunks)
        logger.info("  → %d chunks", len(chunks))

    logger.info("Total: %d chunks from %d papers", len(all_chunks),
                len({c["metadata"]["arxiv_id"] for c in all_chunks}))
    return all_chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    chunks = ingest_all()
    print(f"\nIngested {len(chunks)} chunks from "
          f"{len({c['metadata']['arxiv_id'] for c in chunks})} papers")
```

---

### Wave 5 — Embeddings module

#### Task 5.1 — Create `src/embeddings.py`

```python
"""Embeddings: generate with HuggingFace bge-small-en-v1.5, persist to ChromaDB."""

import logging
from pathlib import Path

import chromadb
from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import Settings
from src.ingestion import ingest_all

logger = logging.getLogger(__name__)

BATCH_SIZE = 64


def get_embedder(settings: Settings) -> HuggingFaceEmbeddings:
    logger.info("Loading embedding model: %s on %s", settings.embedding_model, settings.embedding_device)
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": settings.embedding_device},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_collection(settings: Settings) -> chromadb.Collection:
    Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def embed_and_store(chunks: list[dict], settings: Settings) -> int:
    embedder = get_embedder(settings)
    collection = get_collection(settings)

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [
        f"{c['metadata']['arxiv_id']}_chunk_{c['metadata']['chunk_index']}"
        for c in chunks
    ]

    # Idempotency: skip already-stored chunks
    existing_ids = set(collection.get(ids=ids)["ids"])
    new_indices = [i for i, id_ in enumerate(ids) if id_ not in existing_ids]

    if not new_indices:
        logger.info("All %d chunks already stored — nothing to do", len(chunks))
        return 0

    logger.info("Embedding %d new chunks (skipping %d existing)...",
                len(new_indices), len(existing_ids))

    for batch_start in range(0, len(new_indices), BATCH_SIZE):
        batch_idx = new_indices[batch_start : batch_start + BATCH_SIZE]
        batch_texts = [texts[i] for i in batch_idx]
        batch_embeddings = embedder.embed_documents(batch_texts)
        collection.add(
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=[metadatas[i] for i in batch_idx],
            ids=[ids[i] for i in batch_idx],
        )
        logger.info("  Stored batch %d/%d", batch_start // BATCH_SIZE + 1,
                    -(-len(new_indices) // BATCH_SIZE))

    total = collection.count()
    logger.info("ChromaDB collection '%s' now has %d chunks total", settings.chroma_collection, total)
    return len(new_indices)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = Settings()
    chunks = ingest_all(settings)
    added = embed_and_store(chunks, settings)
    print(f"\nAdded {added} new chunks. Collection ready.")
```

---

### Wave 6 — Build tooling (run in parallel)

#### Task 6.1 — Create `Makefile`

```makefile
.PHONY: install download ingest embed pipeline test lint

install:
	pip install -r requirements.txt

download:
	python scripts/download_papers.py

ingest:
	python src/ingestion.py

embed:
	python src/embeddings.py

pipeline: download ingest embed

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	ruff check src/ tests/ scripts/
	ruff format --check src/ tests/ scripts/

format:
	ruff format src/ tests/ scripts/
```

---

### Wave 7 — Tests (run in parallel)

#### Task 7.1 — Create `tests/test_ingestion.py`

```python
"""Unit tests for src/ingestion.py — no real PDFs or filesystem required."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from config.settings import Settings
from src.ingestion import chunk_pages, extract_pages, ingest_all, load_metadata


@pytest.fixture
def settings():
    return Settings(chunk_size=100, chunk_overlap=10)


@pytest.fixture
def sample_metadata():
    return {
        "arxiv_id": "1706.03762",
        "title": "Attention Is All You Need",
        "authors": ["Vaswani", "Shazeer"],
        "year": 2017,
        "topic": "Transformers",
    }


@pytest.fixture
def sample_pages():
    return [
        {"page": 1, "text": "We propose a new simple network architecture, the Transformer. " * 10},
        {"page": 2, "text": "The dominant sequence transduction models are based on encoder-decoder. " * 10},
    ]


def test_load_metadata(tmp_path):
    meta = [{"arxiv_id": "1706.03762", "title": "Test", "authors": ["A"], "year": 2017, "topic": "T"}]
    meta_file = tmp_path / "papers_metadata.json"
    meta_file.write_text(json.dumps(meta))
    result = load_metadata(meta_file)
    assert "1706.03762" in result
    assert result["1706.03762"]["title"] == "Test"


def test_chunk_pages_returns_chunks(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    assert len(chunks) > 0


def test_chunk_pages_metadata_fields(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    for chunk in chunks:
        assert "text" in chunk
        assert "metadata" in chunk
        meta = chunk["metadata"]
        assert meta["arxiv_id"] == "1706.03762"
        assert meta["title"] == "Attention Is All You Need"
        assert meta["year"] == 2017
        assert "page" in meta
        assert "chunk_index" in meta


def test_chunk_pages_sequential_index(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    indices = [c["metadata"]["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))


def test_chunk_pages_no_empty_chunks(sample_pages, sample_metadata, settings):
    chunks = chunk_pages(sample_pages, sample_metadata, settings.chunk_size, settings.chunk_overlap)
    for chunk in chunks:
        assert chunk["text"].strip()


def test_extract_pages_mocked():
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Sample text from page."
    mock_doc = MagicMock()
    mock_doc.__iter__ = MagicMock(return_value=iter([mock_page, mock_page]))
    mock_doc.__enter__ = MagicMock(return_value=mock_doc)
    mock_doc.__exit__ = MagicMock(return_value=False)

    with patch("src.ingestion.pymupdf.open", return_value=mock_doc):
        pages = extract_pages(Path("fake.pdf"))

    assert len(pages) == 2
    assert pages[0]["text"] == "Sample text from page."
```

#### Task 7.2 — Create `tests/test_embeddings.py`

```python
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


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "The Transformer model uses attention mechanisms.",
            "metadata": {
                "paper_id": "1706.03762",
                "arxiv_id": "1706.03762",
                "title": "Attention Is All You Need",
                "authors": "Vaswani et al.",
                "year": 2017,
                "topic": "Transformers",
                "page": 1,
                "chunk_index": 0,
            },
        },
        {
            "text": "Multi-head attention allows the model to jointly attend to information.",
            "metadata": {
                "paper_id": "1706.03762",
                "arxiv_id": "1706.03762",
                "title": "Attention Is All You Need",
                "authors": "Vaswani et al.",
                "year": 2017,
                "topic": "Transformers",
                "page": 1,
                "chunk_index": 1,
            },
        },
    ]


def test_embed_and_store_adds_new_chunks(sample_chunks, settings):
    mock_embedder = MagicMock()
    mock_embedder.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": []}  # nothing exists yet
    mock_collection.count.return_value = 2

    with patch("src.embeddings.get_embedder", return_value=mock_embedder), \
         patch("src.embeddings.get_collection", return_value=mock_collection):
        added = embed_and_store(sample_chunks, settings)

    assert added == 2
    mock_collection.add.assert_called_once()


def test_embed_and_store_idempotent(sample_chunks, settings):
    mock_embedder = MagicMock()
    mock_collection = MagicMock()
    # Both IDs already exist
    existing_ids = [
        "1706.03762_chunk_0",
        "1706.03762_chunk_1",
    ]
    mock_collection.get.return_value = {"ids": existing_ids}
    mock_collection.count.return_value = 2

    with patch("src.embeddings.get_embedder", return_value=mock_embedder), \
         patch("src.embeddings.get_collection", return_value=mock_collection):
        added = embed_and_store(sample_chunks, settings)

    assert added == 0
    mock_collection.add.assert_not_called()
```

---

## Verification Steps

Run these in order after implementation:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run linter
ruff check src/ tests/ scripts/

# 3. Run tests (no GPU/network required — all mocked)
pytest tests/ -v

# 4. Copy env file
cp .env.example .env

# 5. Download papers (requires internet, ~3-5 min due to rate limiting)
python scripts/download_papers.py

# 6. Run full pipeline
python src/ingestion.py
python src/embeddings.py

# 7. Verify chunk count
python -c "
import chromadb
c = chromadb.PersistentClient(path='data/chroma_db')
col = c.get_collection('research_papers')
print(f'Chunks in ChromaDB: {col.count()}')
"
```

## UAT Checklist

- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `pytest tests/` — all tests pass
- [ ] `python scripts/download_papers.py` — 25/25 papers downloaded to `data/papers/`
- [ ] `python src/embeddings.py` — no errors, logs "Collection ready"
- [ ] ChromaDB collection count ≥ 500 chunks
- [ ] Re-running `python src/embeddings.py` logs "nothing to do" (idempotency)
- [ ] Each chunk has metadata fields: `arxiv_id`, `title`, `authors`, `year`, `page`, `chunk_index`
- [ ] `data/chroma_db/` exists and is non-empty

## Phase Complete Criteria

All UAT items checked + tests green + `ruff check` passing.
Next: `/gsd:plan-phase 2` — RAG Pipeline (retriever + ChatOllama + citations).
