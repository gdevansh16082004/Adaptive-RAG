"""
Route identifier model.
"""

from typing import Literal

from pydantic import BaseModel, Field


class RouteIdentifier(BaseModel):
    """Model for routing queries and selecting relevant documents."""

    route: Literal["index", "general", "search"]
    doc_ids: list[str] = Field(
        default_factory=list,
        description="IDs of documents relevant to the question; "
        "empty unless route is 'index'.",
    )
