"""
Conftest: mock heavy ML dependencies so tests run without installing torch/CUDA.
The actual inference deps (chromadb, langchain_huggingface) are mocked here;
the real packages are only needed when running the pipeline, not the test suite.
"""

import importlib.machinery
import sys
import types
from unittest.mock import MagicMock

# Packages that require torch / CUDA — stub them out so imports succeed
_HEAVY_MOCKS = [
    "chromadb",
    "chromadb.api",
    "chromadb.api.types",
    "langchain_huggingface",
    "langchain_ollama",
    "sentence_transformers",
    # datasets checks torch.__spec__ at import time; mock both to avoid the error
    "datasets",
    "datasets.arrow_dataset",
    "datasets.features",
    "datasets.formatting",
    "datasets.info",
    "datasets.iterable_dataset",
    "datasets.search",
    "datasets.splits",
    "datasets.utils",
    "datasets.utils.logging",
]

for _mod in _HEAVY_MOCKS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# torch needs a real ModuleSpec so importlib.util.find_spec("torch") works
# (datasets checks TORCH_AVAILABLE via find_spec at import time)
if "torch" not in sys.modules:
    _torch = types.ModuleType("torch")
    _torch.__spec__ = importlib.machinery.ModuleSpec("torch", None, origin="mock")
    sys.modules["torch"] = _torch
