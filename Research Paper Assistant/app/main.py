"""Streamlit entrypoint — Research Paper Assistant."""

import streamlit as st

from app.components.chat import render_chat
from app.components.eval_dashboard import render_eval_dashboard
from app.components.paper_browser import render_paper_browser
from config.settings import Settings

# MUST be first Streamlit call
st.set_page_config(
    page_title="Research Paper Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_settings() -> Settings:
    return Settings()


def main() -> None:
    settings = get_settings()

    with st.sidebar:
        render_eval_dashboard()
        st.divider()
        render_paper_browser()

    render_chat(settings)


if __name__ == "__main__":
    main()
