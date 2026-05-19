"""Streaming chat interface with conversation history and citations."""

import streamlit as st

from app.components.sources import render_sources
from config.settings import Settings
from src.pipeline import ask_stream


def _sources_to_dicts(sources) -> list[dict]:
    """Convert Source dataclasses to plain dicts for session_state storage."""
    return [
        {
            "title": s.title,
            "authors": s.authors,
            "year": s.year,
            "arxiv_id": s.arxiv_id,
        }
        for s in sources
    ]


def render_chat(settings: Settings) -> None:
    st.title("📚 Research Paper Assistant")
    st.caption(
        "Ask questions about 25 landmark AI/ML papers — "
        f"powered by **{settings.ollama_model}** via Ollama"
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Replay conversation history on every rerun
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                render_sources(msg["sources"])

    # New user input
    if prompt := st.chat_input("Ask about transformers, RAG, LoRA, RLHF..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Searching papers..."):
                    sources_raw, _chunks, token_gen = ask_stream(prompt, settings)
                sources = _sources_to_dicts(sources_raw)

                # Show sources before streaming starts
                if sources:
                    render_sources(sources)

                # Stream tokens — returns full answer string when complete
                answer = st.write_stream(token_gen)

            except Exception as exc:
                answer = (
                    "Could not reach Ollama. Make sure `ollama serve` is running "
                    f"and `{settings.ollama_model}` is pulled.\n\n"
                    f"```\n{exc}\n```"
                )
                sources = []
                st.markdown(answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )
