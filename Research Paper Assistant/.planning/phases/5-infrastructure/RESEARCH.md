# Research — Phase 5: Infrastructure & Deployment

> Researched: 2026-05-19 | Status: Complete

---

## Docker

### Base image

`python:3.11-slim` — ~130MB, has pip, no dev tools. Use 3.11 for reproducibility (project requires >=3.11).

### CPU-only torch

`sentence-transformers` pulls in torch. Default torch is ~3GB (GPU). CPU-only is ~500MB:

```dockerfile
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
```

Install torch first, then requirements — pip reuses the already-installed CPU torch and doesn't re-download the GPU one.

### Non-root user (HF Spaces requirement)

```dockerfile
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
```

HF Spaces runs containers as uid 1000. Use this exact pattern.

### Port

HF Spaces Docker Spaces expect **port 7860** (not 8501). Override Streamlit's default:

```dockerfile
EXPOSE 7860
CMD ["streamlit", "run", "app/main.py", \
     "--server.port=7860", "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

### ENV defaults for container

```dockerfile
ENV EMBEDDING_DEVICE=cpu \
    OLLAMA_BASE_URL=http://localhost:11434
```

`EMBEDDING_DEVICE=cpu` ensures no CUDA errors on CPU-only HF Spaces free tier.

---

## HF Spaces

### README.md frontmatter (must be at top of root README.md)

```yaml
---
title: Research Paper Assistant
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---
```

HF Spaces reads this to know the space type (Docker) and which port to expose.

### Deployment via git push

HF Spaces is a git remote. Push the repo to deploy:

```bash
git remote add space https://huggingface.co/spaces/USERNAME/REPO
git push space main --force
```

For GitHub Actions, use `HF_TOKEN` secret (a HuggingFace write token):

```yaml
- name: Push to HF Spaces
  env:
    HF_TOKEN: ${{ secrets.HF_TOKEN }}
  run: |
    git remote add space https://GabrielMacGregor:$HF_TOKEN@huggingface.co/spaces/GabrielMacGregor/research-paper-assistant
    git push space main --force
```

The HF Space must already exist. Create it at https://huggingface.co/new-space with SDK = Docker.

---

## GitHub Actions

### CI workflow trigger

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

### Pip caching (speeds CI from ~4min to ~30s on repeat runs)

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
    cache: "pip"
    cache-dependency-path: requirements-ci.txt
```

### requirements-ci.txt (lightweight — heavy packages mocked in conftest.py)

CI needs only the subset that isn't mocked:

```
pydantic-settings==2.8.1
python-dotenv==1.1.0
pymupdf==1.27.2
langchain-core
langchain-text-splitters
ragas==0.2.15
pandas
numpy
streamlit==1.45.1
pytest==8.3.5
pytest-cov==6.1.0
ruff==0.11.10
```

Does NOT include: `torch`, `sentence-transformers`, `chromadb`, `langchain-huggingface`, `langchain-ollama` — these are all mocked in `tests/conftest.py`, so tests pass without them.

### Deploy workflow trigger

Only on push to `main` (not PRs — avoid deploying broken code):

```yaml
on:
  push:
    branches: [main]
```

Use `needs: test` so deploy only runs if CI passes.

---

## HF Spaces Demo Strategy

Ollama is NOT available on HF Spaces free tier. The demo approach:

| Feature | Works in Demo? | How |
|---|---|---|
| Paper browser (sidebar) | ✅ | Reads `data/papers_metadata.json` |
| RAGAS scores (sidebar) | ✅ | Reads committed `evaluation/results/ragas_scores.json` |
| Chat — submit question | ❌ → friendly error | `ask_stream()` catches exception, shows message |

**Action**: remove `evaluation/results/ragas_scores.json` from `.gitignore` and commit a demo scores file. When user runs `make eval` on their GPU machine, real scores overwrite it.

---

## .dockerignore

Exclude large files from build context to keep docker build fast:

```
.git
.github
.planning
.venv
venv
data/papers/
data/chroma_db/
__pycache__
*.pyc
*.pyo
.pytest_cache
.coverage
htmlcov
get-shit-done
.env
evaluation/results/ragas_scores.json
```

Note: `evaluation/results/ragas_scores.json` IS included in the image via the explicit COPY (overriding dockerignore) — wait, no: dockerignore exclusions apply to COPY. So if we want the demo scores in the image, we should NOT exclude it from dockerignore.

**Revised**: include `evaluation/results/ragas_scores.json` in the image (it's committed and ~2KB). Remove it from `.dockerignore`.

---

## Gotchas

1. HF Spaces requires uid 1000 — files copied by root before `USER user` are owned by root. Use `--chown=user:user` in COPY:
   ```dockerfile
   COPY --chown=user:user . .
   ```
2. `pydantic>=2.0,<2.13` in requirements.txt conflicts with newer pydantic (2.13+ is installed and works fine). Remove upper bound to `pydantic>=2.0`.
3. HF Spaces free tier has no GPU — `EMBEDDING_DEVICE=cpu` is required.
4. `streamlit run` needs `--server.headless=true` to avoid browser auto-open in container.
5. GitHub Actions `ubuntu-latest` doesn't have torch — conftest.py mocks handle this correctly.
6. HF Space must be created manually first at huggingface.co/new-space before the deploy workflow can push.
