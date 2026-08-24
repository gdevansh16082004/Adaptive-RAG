"""
Document info model for API responses.
"""

from pydantic import BaseModel


class DocumentInfo(BaseModel):
    """Public shape of a registered document."""

    doc_id: str
    user_id: str
    filename: str
    description: str
    num_chunks: int
    created_at: str
