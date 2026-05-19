"""Inline citations component rendered below each assistant message."""

import streamlit as st


def render_sources(sources: list[dict]) -> None:
    """Render a collapsible sources block.

    Args:
        sources: list of dicts with keys title, authors, year, arxiv_id.
    """
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for s in sources:
            arxiv_id = s.get("arxiv_id", "")
            title = s.get("title", "Unknown")
            year = s.get("year", "")
            authors = s.get("authors", "")
            st.markdown(
                f"**{title}** ({year})  \n"
                f"_{authors}_  \n"
                f"[arxiv.org/abs/{arxiv_id}](https://arxiv.org/abs/{arxiv_id})"
            )
