from typing import List, Optional, TypedDict
from langchain_core.documents import Document

class State(TypedDict, total=False):
    """
    Represents the state of the Agentic RAG workflow.
    All fields are optional (total=False) as they are populated by different nodes.
    """
    # --- User Input ---
    question: str
    current_query: str
    user_clearance: int
    user_department: str

    # --- Knowledge Base Path ---
    kb_docs: List[Document]
    kb_grade: str  # "good" or "weak"

    # --- Web Search Path ---
    web_docs: List[Document]
    web_grade: str  # "good" or "weak"

    # --- Generation Output ---
    generation: str
    source_used: str  # "Knowledge Base", "Web", or "Fallback"

    # --- Observability ---
    trace: List[str]
    citations: str
    retry_count: int
