"""
State model for the graph-based RAG system.
"""

from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


class Source(TypedDict, total=False):
    """A single source citation from a retrieved chunk."""

    filename: str
    page: Optional[int]
    doc_id: str
    snippet: str


class State(TypedDict):
    """State schema for the RAG graph."""

    messages: Annotated[list[AnyMessage], add_messages]
    binary_score: Optional[str]
    route: Optional[str]
    latest_query: Optional[str]
    user_id: Optional[str]
    doc_ids: Optional[List[str]]
    context: Optional[str]
    rewrite_count: Optional[int]
    verify_count: Optional[int]
    verify_score: Optional[str]
    sources: Optional[List[Source]]
