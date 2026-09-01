"""
Structured API response models.

Every endpoint wraps its return value in an APIResponse envelope so clients
get a predictable shape on both success and failure paths.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable error descriptor."""

    code: str = Field(description="Snake-case error category, e.g. 'qdrant_unavailable'.")
    message: str = Field(description="Human-readable explanation.")


class APIResponse(BaseModel):
    """
    Uniform response envelope for every REST endpoint.

    Successful responses carry ``data`` (and ``success=True``);
    error responses carry ``error`` (and ``success=False``).
    """

    success: bool = True
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
