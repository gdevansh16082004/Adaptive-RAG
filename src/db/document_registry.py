"""
Synchronous MongoDB-backed document registry.

Uses pymongo (not motor) so it can be called from synchronous LangGraph nodes
and from async FastAPI routes alike. One row per uploaded document.
"""

import logging
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError

from src.core.config import settings

logger = logging.getLogger(__name__)


class RegistryUnavailableError(Exception):
    """Raised when the document registry cannot be reached or written to."""


_registry: MongoClient = MongoClient(
    settings.MONGODB_URL,
    serverSelectionTimeoutMS=5000,
)
documents = _registry[settings.MONGODB_DB_NAME]["documents"]


def _ensure_indexes() -> None:
    """Create uniqueness indexes once; startup must not crash if Mongo is down."""
    try:
        documents.create_index([("doc_id", ASCENDING)], unique=True)
        documents.create_index(
            [("user_id", ASCENDING), ("content_sha256", ASCENDING)],
            unique=True,
        )
    except PyMongoError as e:
        logger.warning("Could not ensure document registry indexes: %s", e)


_ensure_indexes()


def register_document(
    *,
    doc_id: str,
    user_id: str,
    filename: str,
    description_raw: str,
    description_enhanced: str,
    content_sha256: str,
    num_chunks: int,
) -> dict:
    """
    Insert a new document record into the registry.

    Args:
        doc_id: Unique document identifier.
        user_id: Owner of the document.
        filename: Original uploaded filename.
        description_raw: Description as provided by the user.
        description_enhanced: LLM-enhanced tool description.
        content_sha256: SHA-256 hash of the file content.
        num_chunks: Number of chunks stored in the vector database.

    Returns:
        The raw registry record as inserted.

    Raises:
        RegistryUnavailableError: On any persistence failure.
    """
    record = {
        "doc_id": doc_id,
        "user_id": user_id,
        "filename": filename,
        "description_raw": description_raw,
        "description_enhanced": description_enhanced,
        "content_sha256": content_sha256,
        "num_chunks": num_chunks,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        documents.insert_one(dict(record))
    except PyMongoError as e:
        raise RegistryUnavailableError(f"Failed to register document: {e}") from e
    return record


def find_duplicate(user_id: str, content_sha256: str) -> dict | None:
    """
    Find an earlier upload of identical content by the same user.

    Args:
        user_id: Owner of the documents.
        content_sha256: SHA-256 hash of the file content.

    Returns:
        The matching document record, or None if not found.

    Raises:
        RegistryUnavailableError: On lookup failure.
    """
    try:
        return documents.find_one(
            {"user_id": user_id, "content_sha256": content_sha256}
        )
    except PyMongoError as e:
        raise RegistryUnavailableError(f"Registry lookup failed: {e}") from e


def list_documents(user_id: str) -> list[dict]:
    """
    List all documents owned by a user, newest first.

    Args:
        user_id: Owner of the documents.

    Returns:
        List of serialized document records.

    Raises:
        RegistryUnavailableError: On listing failure.
    """
    try:
        cursor = (
            documents.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
        )
        return [serialize(doc) for doc in cursor]
    except PyMongoError as e:
        raise RegistryUnavailableError(f"Registry listing failed: {e}") from e


def get_document(doc_id: str) -> dict | None:
    """
    Fetch a single document record by id.

    Args:
        doc_id: Unique document identifier.

    Returns:
        The serialized document record, or None if not found.

    Raises:
        RegistryUnavailableError: On lookup failure.
    """
    try:
        doc = documents.find_one({"doc_id": doc_id})
        return serialize(doc) if doc else None
    except PyMongoError as e:
        raise RegistryUnavailableError(f"Registry lookup failed: {e}") from e


def delete_document(doc_id: str) -> bool:
    """
    Delete a document record from the registry.

    Args:
        doc_id: Unique document identifier.

    Returns:
        True if a record was deleted, False otherwise.

    Raises:
        RegistryUnavailableError: On deletion failure.
    """
    try:
        result = documents.delete_one({"doc_id": doc_id})
        return result.deleted_count > 0
    except PyMongoError as e:
        raise RegistryUnavailableError(f"Registry deletion failed: {e}") from e


def serialize(doc: dict) -> dict:
    """
    Convert a registry record into its JSON-safe API shape.

    Args:
        doc: Raw registry record containing ObjectId and datetime values.

    Returns:
        Record with doc_id, user_id, filename, description (enhanced),
        num_chunks and created_at as ISO string.
    """
    created_at = doc["created_at"]
    return {
        "doc_id": doc["doc_id"],
        "user_id": doc["user_id"],
        "filename": doc["filename"],
        "description": doc["description_enhanced"],
        "num_chunks": doc["num_chunks"],
        "created_at": (
            created_at.isoformat() if isinstance(created_at, datetime)
            else created_at
        ),
    }
