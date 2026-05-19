FROM python:3.11-slim

# Install CPU-only torch first to prevent pip from pulling the 3GB GPU variant
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Non-root user — HF Spaces requires uid 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    EMBEDDING_DEVICE=cpu \
    OLLAMA_BASE_URL=http://localhost:11434

WORKDIR /home/user/app

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/_stcore/health')"

CMD ["streamlit", "run", "app/main.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
