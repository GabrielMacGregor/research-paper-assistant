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
    logger.info(
        "Loading embedding model: %s on %s",
        settings.embedding_model,
        settings.embedding_device,
    )
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
    if not chunks:
        logger.warning("No chunks to embed.")
        return 0

    embedder = get_embedder(settings)
    collection = get_collection(settings)

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [
        f"{c['metadata']['arxiv_id']}_chunk_{c['metadata']['chunk_index']}"
        for c in chunks
    ]

    # Idempotency: only embed chunks not already stored
    existing_ids = set(collection.get(ids=ids)["ids"])
    new_indices = [i for i, id_ in enumerate(ids) if id_ not in existing_ids]

    if not new_indices:
        logger.info("All %d chunks already stored — nothing to do.", len(chunks))
        return 0

    logger.info(
        "Embedding %d new chunks (skipping %d already stored)...",
        len(new_indices),
        len(existing_ids),
    )

    total_batches = -(-len(new_indices) // BATCH_SIZE)  # ceiling division
    for batch_num, batch_start in enumerate(range(0, len(new_indices), BATCH_SIZE), start=1):
        batch_idx = new_indices[batch_start : batch_start + BATCH_SIZE]
        batch_texts = [texts[i] for i in batch_idx]
        batch_embeddings = embedder.embed_documents(batch_texts)
        collection.add(
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=[metadatas[i] for i in batch_idx],
            ids=[ids[i] for i in batch_idx],
        )
        logger.info("  Stored batch %d/%d", batch_num, total_batches)

    total = collection.count()
    logger.info(
        "ChromaDB collection '%s' now has %d chunks total.",
        settings.chroma_collection,
        total,
    )
    return len(new_indices)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = Settings()
    chunks = ingest_all(settings)
    added = embed_and_store(chunks, settings)
    print(f"\nAdded {added} new chunks. Collection is ready.")
