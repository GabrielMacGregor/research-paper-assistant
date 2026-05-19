"""PDF ingestion: parse with PyMuPDF, chunk with LangChain RecursiveCharacterTextSplitter."""

import json
import logging
from pathlib import Path

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config.settings import Settings

logger = logging.getLogger(__name__)


def load_metadata(metadata_path: Path = Path("data/papers_metadata.json")) -> dict[str, dict]:
    with open(metadata_path, encoding="utf-8") as f:
        papers = json.load(f)
    return {p["arxiv_id"]: p for p in papers}


def extract_pages(pdf_path: Path) -> list[dict]:
    """Extract text page-by-page from a PDF. Returns [{page: int, text: str}, ...]."""
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
    """Split page texts into overlapping chunks with paper metadata attached."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    authors = paper_metadata["authors"]
    authors_str = (
        ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    )
    base_meta = {
        "paper_id": paper_metadata["arxiv_id"],
        "title": paper_metadata["title"],
        "authors": authors_str,
        "year": paper_metadata["year"],
        "arxiv_id": paper_metadata["arxiv_id"],
        "topic": paper_metadata.get("topic", ""),
    }
    chunks: list[dict] = []
    chunk_index = 0
    for page_info in pages:
        for text in splitter.split_text(page_info["text"]):
            if text.strip():
                chunks.append({
                    "text": text,
                    "metadata": {
                        **base_meta,
                        "page": page_info["page"],
                        "chunk_index": chunk_index,
                    },
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

    pdf_files = sorted(papers_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning("No PDFs found in %s — run scripts/download_papers.py first", papers_dir)
        return []

    for pdf_path in pdf_files:
        arxiv_id = pdf_path.stem
        if arxiv_id not in metadata_by_id:
            logger.warning("No metadata for %s — skipping", arxiv_id)
            continue
        paper_meta = metadata_by_id[arxiv_id]
        logger.info("Ingesting %s: %s", arxiv_id, paper_meta["title"])
        chunks = ingest_paper(pdf_path, paper_meta, settings)
        all_chunks.extend(chunks)
        logger.info("  → %d chunks", len(chunks))

    paper_count = len({c["metadata"]["arxiv_id"] for c in all_chunks})
    logger.info("Total: %d chunks from %d papers", len(all_chunks), paper_count)
    return all_chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    chunks = ingest_all()
    paper_ids = {c["metadata"]["arxiv_id"] for c in chunks}
    print(f"\nIngested {len(chunks)} chunks from {len(paper_ids)} papers.")
