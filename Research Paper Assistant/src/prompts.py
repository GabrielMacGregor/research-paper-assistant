"""RAG prompt templates."""

from langchain_core.prompts import ChatPromptTemplate

_SYSTEM = """\
You are a research assistant specializing in AI/ML papers.
Answer the question ONLY using the context below — do not use outside knowledge.
Always cite the paper(s) you drew from (title and year) at the end of your answer.
If the context does not contain enough information to answer, respond with exactly:
"I couldn't find relevant information in the indexed papers."

Context:
{context}
"""

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "{question}"),
])
