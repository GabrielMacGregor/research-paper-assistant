"""Sidebar widget listing all indexed papers."""

import json
from pathlib import Path

import streamlit as st

_METADATA_PATH = Path("data/papers_metadata.json")


def load_papers(path: Path = _METADATA_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def render_paper_browser() -> None:
    st.subheader("Indexed Papers")
    papers = load_papers()

    if not papers:
        st.warning("No papers indexed. Run `make pipeline` first.")
        return

    st.caption(f"{len(papers)} papers in knowledge base")

    for paper in papers:
        title_short = paper["title"][:48] + ("…" if len(paper["title"]) > 48 else "")
        with st.expander(f"{title_short} ({paper['year']})"):
            authors = paper["authors"]
            if isinstance(authors, list):
                author_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    author_str += " et al."
            else:
                author_str = str(authors)
            st.markdown(f"**Authors:** {author_str}")
            st.markdown(f"**Topic:** {paper['topic']}")
            arxiv_id = paper["arxiv_id"]
            st.markdown(
                f"**arXiv:** [{arxiv_id}](https://arxiv.org/abs/{arxiv_id})"
            )
