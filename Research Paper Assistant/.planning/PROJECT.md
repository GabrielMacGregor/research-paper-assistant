# Research Paper Assistant

## Overview

A production-quality RAG (Retrieval-Augmented Generation) application that answers questions about AI/ML research papers. Built as a portfolio project to demonstrate mastery of the modern LLM ecosystem — not just API calls, but a complete system with quantitative evaluation and production-ready architecture.

## Purpose & Strategic Value

- **Target audience**: AI/ML engineering recruiters (international)
- **Differentiator**: RAGAS evaluation dashboard showing quantitative quality scores — what production RAG systems actually need, and what almost no portfolio shows
- **Data source**: arXiv public PDFs (20–30 landmark AI/ML papers)
- **Demo platform**: Hugging Face Spaces (free, highly visible to AI recruiters)

## Problem Statement

Candidates applying to AI/ML roles typically show "I connected LangChain + OpenAI + Chroma." This project shows: I know how to build a RAG system that can be measured, debugged, and improved — with faithfulness, relevancy, and context precision scores.

## Goals

1. Ingest and index 20–30 landmark AI/ML papers (arXiv PDFs)
2. Answer natural language questions with relevant, cited responses
3. Provide quantitative quality evaluation via RAGAS
4. Deploy a public demo accessible to recruiters

## Non-Goals

- Real-time arXiv indexing / continuous ingestion
- Multi-user authentication
- Paid SaaS features

## Key Stakeholders

- **Owner**: Gabriel Macgregor
- **Audience**: International AI/ML engineering recruiters

## Tech Stack

| Layer | Technology | Rationale |
|---|---|---|
| PDF Parsing | PyMuPDF (fitz) | Fast, accurate, handles arXiv PDFs well |
| Chunking | LangChain TextSplitter | Configurable overlap, battle-tested |
| Embeddings | HuggingFace BAAI/bge-small-en-v1.5 | Free, local, no API cost, strong quality |
| Vector Store | ChromaDB (local) | Zero cost, persistent, good DX |
| LLM | OpenAI GPT-4o-mini + Google Gemini Flash | Configurable via .env, both cheap/free |
| Evaluation | RAGAS | Industry-standard RAG evaluation framework |
| Interface | Streamlit | Rapid UI, HF Spaces compatible |
| Container | Docker | Reproducible environment |
| CI/CD | GitHub Actions | Automated testing on push |
| Deploy | Hugging Face Spaces | Free, recruiter-visible |

## Architecture

```
PDFs → PyMuPDF Parsing → LangChain Chunking (overlap)
                                    ↓
                        HuggingFace Embeddings
                                    ↓
                         ChromaDB (local persist)

User Question → Embed → Semantic Search (+ MMR diversity)
                                    ↓
                          Top-K relevant chunks
                                    ↓
              Prompt template (question + chunks + citation instruction)
                                    ↓
                    LLM (OpenAI / Gemini — configurable)
                                    ↓
                   Answer with paper citations + RAGAS scores
```

## Paper Corpus (Target: 25 papers)

| # | Paper | Year | Domain |
|---|---|---|---|
| 1 | Attention Is All You Need | 2017 | Transformers |
| 2 | BERT | 2018 | Language Models |
| 3 | GPT-2 | 2019 | Language Models |
| 4 | GPT-3 | 2020 | Language Models |
| 5 | RAG (Lewis et al.) | 2020 | Retrieval |
| 6 | DPR | 2020 | Retrieval |
| 7 | InstructGPT | 2022 | RLHF |
| 8 | Chain-of-Thought Prompting | 2022 | Prompting |
| 9 | ReAct | 2022 | Agents |
| 10 | Self-Consistency | 2022 | Prompting |
| 11 | LoRA | 2021 | Fine-tuning |
| 12 | CLIP | 2021 | Multimodal |
| 13 | Constitutional AI | 2022 | Safety |
| 14 | LLaMA | 2023 | Open Models |
| 15 | LLaMA 2 | 2023 | Open Models |
| 16 | Mistral 7B | 2023 | Open Models |
| 17 | Mixtral | 2024 | MoE |
| 18 | Gemini | 2023 | Multimodal |
| 19 | ColBERT | 2020 | Retrieval |
| 20 | FAISS | 2017 | Vector Search |
| 21 | AlphaFold2 | 2021 | Biology/ML |
| 22 | Stable Diffusion | 2022 | Generative |
| 23 | DALL-E | 2021 | Generative |
| 24 | Phi-2 | 2023 | Small Models |
| 25 | RWKV | 2023 | Architecture |

## Success Metrics

- RAGAS faithfulness ≥ 0.85
- RAGAS answer_relevancy ≥ 0.80
- RAGAS context_precision ≥ 0.75
- All 25 papers ingested and queryable
- Public HF Spaces demo live
- CI passing on main branch

## Milestones

| Milestone | Description |
|---|---|
| v0.1 | Data pipeline: ingest + embed + store all 25 papers |
| v0.2 | RAG pipeline: retrieval + LLM + citation format |
| v0.3 | Evaluation: RAGAS scores on test question set |
| v0.4 | Interface: Streamlit app with conversation history |
| v1.0 | Production: Docker + CI/CD + HF Spaces deploy |

## Project Metadata

- **Created**: 2026-05-19
- **Type**: Portfolio / Open Source
- **Language**: Python 3.11+
- **License**: MIT
