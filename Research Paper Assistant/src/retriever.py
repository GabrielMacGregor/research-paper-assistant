"""Semantic retrieval with MMR from ChromaDB."""

import logging
from typing import Any

import chromadb
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import Settings

logger = logging.getLogger(__name__)

FETCH_MULTIPLIER = 3  # retrieve 3x candidates before MMR filtering


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    return float(np.dot(a_arr, b_arr) / denom) if denom > 0 else 0.0


def _mmr(
    query_embedding: list[float],
    candidates: list[dict[str, Any]],
    k: int,
    lambda_mult: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Maximal Marginal Relevance selection.
    lambda_mult=1 → pure similarity; lambda_mult=0 → pure diversity.
    """
    if len(candidates) <= k:
        return candidates

    embs = [c["embedding"] for c in candidates]
    query_sims = [_cosine_sim(query_embedding, e) for e in embs]

    selected: list[int] = []
    remaining = list(range(len(candidates)))

    while len(selected) < k and remaining:
        if not selected:
            best = max(remaining, key=lambda i: query_sims[i])
        else:
            selected_embs = [embs[i] for i in selected]
            best = max(
                remaining,
                key=lambda i: (
                    lambda_mult * query_sims[i]
                    - (1 - lambda_mult) * max(_cosine_sim(embs[i], s) for s in selected_embs)
                ),
            )
        selected.append(best)
        remaining.remove(best)

    return [candidates[i] for i in selected]


def retrieve(
    query: str,
    settings: Settings,
    use_mmr: bool = True,
) -> list[dict[str, Any]]:
    """
    Retrieve top-K relevant chunks for a query.
    Returns list of {text, metadata, score} dicts.
    """
    embedder = HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": settings.embedding_device},
        encode_kwargs={"normalize_embeddings": True},
    )
    query_embedding = embedder.embed_query(query)

    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_collection(settings.chroma_collection)

    fetch_k = settings.top_k * FETCH_MULTIPLIER
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(fetch_k, collection.count()),
        include=["documents", "metadatas", "distances", "embeddings"],
    )

    candidates = [
        {
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score": 1.0 - results["distances"][0][i],  # distance → similarity
            "embedding": results["embeddings"][0][i],
        }
        for i in range(len(results["documents"][0]))
    ]

    if use_mmr:
        selected = _mmr(query_embedding, candidates, k=settings.top_k)
    else:
        selected = candidates[: settings.top_k]

    # Strip raw embeddings from output (not needed downstream)
    for chunk in selected:
        chunk.pop("embedding", None)

    logger.info("Retrieved %d chunks for query: %s", len(selected), query[:60])
    return selected
