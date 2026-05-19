"""RAG pipeline: query → retrieve → prompt → LLM → structured response."""

import argparse
import logging
from collections.abc import Generator
from dataclasses import dataclass

from config.settings import Settings
from src.llm import get_llm
from src.prompts import RAG_PROMPT
from src.retriever import retrieve

logger = logging.getLogger(__name__)

NO_CONTEXT_REPLY = "I couldn't find relevant information in the indexed papers."


@dataclass
class Source:
    title: str
    authors: str
    year: int
    arxiv_id: str


@dataclass
class RAGResponse:
    answer: str
    sources: list[Source]
    context_chunks: list[dict]
    query: str = ""


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block."""
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk["metadata"]
        parts.append(
            f"[{i}] {meta['title']} ({meta['year']}) — {meta['authors']}\n"
            f"Page {meta['page']}:\n{chunk['text']}"
        )
    return "\n\n---\n\n".join(parts)


def _extract_sources(chunks: list[dict]) -> list[Source]:
    """Deduplicate chunks and build Source objects from metadata."""
    seen: set[str] = set()
    sources: list[Source] = []
    for chunk in chunks:
        meta = chunk["metadata"]
        arxiv_id = meta["arxiv_id"]
        if arxiv_id not in seen:
            seen.add(arxiv_id)
            sources.append(Source(
                title=meta["title"],
                authors=meta["authors"],
                year=meta["year"],
                arxiv_id=arxiv_id,
            ))
    return sources


def ask(query: str, settings: Settings | None = None) -> RAGResponse:
    """Full RAG pipeline: query → answer with citations."""
    if settings is None:
        settings = Settings()

    chunks = retrieve(query, settings)

    if not chunks:
        logger.warning("No relevant chunks found for query.")
        return RAGResponse(
            answer=NO_CONTEXT_REPLY,
            sources=[],
            context_chunks=[],
            query=query,
        )

    context = _build_context(chunks)
    llm = get_llm(settings)
    messages = RAG_PROMPT.format_messages(context=context, question=query)
    response = llm.invoke(messages)
    answer = response.content

    return RAGResponse(
        answer=answer,
        sources=_extract_sources(chunks),
        context_chunks=chunks,
        query=query,
    )


def ask_stream(
    query: str,
    settings: Settings | None = None,
) -> tuple[list[Source], list[dict], Generator[str, None, None]]:
    """Streaming variant of ask().

    Returns (sources, context_chunks, token_generator) so the caller can
    render sources before streaming starts, then yield tokens into st.write_stream.
    ask() is unchanged — all existing tests remain valid.
    """
    if settings is None:
        settings = Settings()

    chunks = retrieve(query, settings)

    if not chunks:
        logger.warning("No relevant chunks found for query.")

        def _no_context() -> Generator[str, None, None]:
            yield NO_CONTEXT_REPLY

        return [], [], _no_context()

    context = _build_context(chunks)
    sources = _extract_sources(chunks)
    llm = get_llm(settings)
    messages = RAG_PROMPT.format_messages(context=context, question=query)

    def _stream() -> Generator[str, None, None]:
        for chunk in llm.stream(messages):
            yield chunk.content

    return sources, chunks, _stream()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ask a question about AI/ML papers.")
    parser.add_argument("--query", required=True, help="Question to ask")
    parser.add_argument("--no-mmr", action="store_true", help="Disable MMR, use plain similarity")
    args = parser.parse_args()

    settings = Settings()
    response = ask(args.query, settings)

    print(f"\n{'=' * 60}")
    print(f"Query: {response.query}")
    print(f"{'=' * 60}")
    print(f"\nAnswer:\n{response.answer}")
    print(f"\nSources ({len(response.sources)}):")
    for s in response.sources:
        print(f"  • {s.title} ({s.year}) — arxiv:{s.arxiv_id}")
    print(f"\nContext chunks used: {len(response.context_chunks)}")
