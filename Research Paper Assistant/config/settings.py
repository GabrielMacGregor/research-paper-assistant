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
