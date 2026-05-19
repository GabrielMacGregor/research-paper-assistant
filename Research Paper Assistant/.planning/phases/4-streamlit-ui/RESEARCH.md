# Research — Phase 4: Streamlit Interface

> Researched: 2026-05-19 | Status: Complete

## Streamlit Version & Install

```
streamlit==1.45.1   # latest stable as of 2026-05
```

Add to `requirements.txt`. HF Spaces supports any Streamlit 1.x.

---

## Chat API (available since Streamlit 1.20)

```python
# Chat bubbles
with st.chat_message("user"):     # or "assistant"
    st.markdown("Hello!")

# Input box — returns str or None (None when empty / user hasn't submitted)
if prompt := st.chat_input("Ask a question..."):
    ...  # only enters when user submits
```

### Session State for Conversation History

```python
# Initialize once per session
if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay history on every rerun
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Append new messages
st.session_state.messages.append({"role": "user", "content": prompt})
```

**Key rule**: Store only JSON-serializable types in `session_state` — use `dict` not dataclasses for sources.

---

## Layout & Sidebar

```python
st.set_page_config(
    page_title="Research Paper Assistant",
    page_icon="📚",
    layout="wide",
)

with st.sidebar:
    st.header("RAGAS Scores")
    # ... metrics
    st.divider()
    st.header("Papers")
    # ... paper browser
```

### Metrics Widget

```python
st.metric(
    label="Faithfulness",
    value="0.891",
    delta="+0.041 vs threshold",
    delta_color="normal",   # green if positive, red if negative
)
```

### Expander for Paper Browser

```python
for paper in papers:
    with st.expander(f"{paper['title'][:45]}... ({paper['year']})"):
        st.markdown(f"**Authors:** {paper['authors']}")
        st.markdown(f"[arXiv:{paper['arxiv_id']}](https://arxiv.org/abs/{paper['arxiv_id']})")
```

---

## Spinner (blocking calls)

Ollama inference is synchronous and slow (~5-15s). Use spinner — no streaming needed for MVP:

```python
with st.spinner("Searching papers and generating answer..."):
    response = ask(prompt, settings)
```

Streaming is possible via `st.write_stream()` + `ChatOllama.stream()` but requires refactoring `pipeline.py` — out of scope for this phase.

---

## Error Handling Pattern

Ollama may not be running in demo environments. Always wrap the pipeline call:

```python
try:
    response = ask(prompt, settings)
except Exception as e:
    st.error(f"Could not reach Ollama. Make sure `ollama serve` is running.\n\n`{e}`")
    return
```

---

## Graceful Degradation

The app must start and render even when:
- ChromaDB is not populated (no papers indexed yet)
- RAGAS scores file doesn't exist (evaluation not run)
- Ollama is not running (show error only on submit)

Use `Path.exists()` checks before loading any generated files.

---

## Testing Streamlit Components

For pure functions (data loaders), use standard pytest — no Streamlit needed:

```python
def test_load_scores_returns_none_when_missing(tmp_path):
    assert load_scores(tmp_path / "scores.json") is None

def test_load_scores_parses_aggregate(tmp_path):
    f = tmp_path / "scores.json"
    f.write_text('{"aggregate": {"faithfulness": 0.89}}')
    result = load_scores(f)
    assert result["aggregate"]["faithfulness"] == 0.89
```

`streamlit.testing.v1.AppTest` exists but is integration-level and requires the full app to run — skip for this phase.

---

## Makefile Target

```makefile
ui:
	streamlit run app/main.py
```

---

## Gotchas

1. `st.session_state` keys must be strings — avoid using dataclass instances as values
2. `st.chat_input` reruns the whole script on submit — always replay history before showing new messages
3. `st.set_page_config` must be the **first** Streamlit call in `app/main.py`
4. Sidebar width is fixed — keep paper titles short (truncate to ~50 chars)
5. `st.metric` `delta_color="normal"` = green when positive, red when negative — good for threshold deltas
6. On HF Spaces, Ollama won't be available — the app should show a friendly message, not crash
