"""Local LLM wrapper via Ollama + ChatOllama."""

from langchain_ollama import ChatOllama

from config.settings import Settings


def get_llm(settings: Settings) -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
    )
