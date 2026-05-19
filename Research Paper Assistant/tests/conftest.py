"""
Conftest: mock heavy ML dependencies so tests run without installing torch/CUDA.
The actual inference deps (chromadb, langchain_huggingface) are mocked here;
the real packages are only needed when running the pipeline, not the test suite.
"""

import sys
from unittest.mock import MagicMock

# Packages that require torch / CUDA — stub them out so imports succeed
_HEAVY_MOCKS = [
    "chromadb",
    "chromadb.api",
    "chromadb.api.types",
    "langchain_huggingface",
    "langchain_ollama",
    "sentence_transformers",
    "torch",
]

for _mod in _HEAVY_MOCKS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
