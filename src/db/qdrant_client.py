"""
Qdrant client and vector store access for document storage.

A single process-wide QdrantClient is reused for every request so HTTP
sessions are not re-created per query (important against Qdrant Cloud).
"""

import logging

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from src.core.config import settings

logger = logging.getLogger(__name__)

# Module-level singletons: one connection pool, one collection readiness flag
_client: QdrantClient | None = None
_collection_ready = False


class QdrantUnavailableError(Exception):
    """Raised when Qdrant cannot be reached or the collection cannot be prepared."""


def get_qdrant_client() -> QdrantClient:
    """
    Get the shared Qdrant client singleton, verifying connectivity on creation.

    Returns:
        A QdrantClient connected to settings.QDRANT_URL.

    Raises:
        QdrantUnavailableError: If Qdrant cannot be reached.
    """
    global _client
    if _client is None:
        try:
            candidate = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                timeout=15,
            )
            candidate.get_collections()  # fail fast on a bad URL or key
            _client = candidate
        except Exception as e:
            logger.error("Cannot reach Qdrant at %s: %s", settings.QDRANT_URL, e)
            raise QdrantUnavailableError(
                f"Cannot reach Qdrant at {settings.QDRANT_URL}: {e}"
            ) from e
    return _client


def ensure_docs_collection(dimension: int) -> None:
    """
    Create the documents collection and its payload indexes if needed.

    Idempotent; the work is skipped entirely once it has succeeded in this
    process.

    Args:
        dimension: Embedding vector size for the collection.

    Raises:
        QdrantUnavailableError: If the collection cannot be prepared.
    """
    global _collection_ready
    if _collection_ready:
        return

    client = get_qdrant_client()
    try:
        if not client.collection_exists(settings.DOCS_COLLECTION):
            client.create_collection(
                collection_name=settings.DOCS_COLLECTION,
                vectors_config=models.VectorParams(
                    size=dimension,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection %s", settings.DOCS_COLLECTION)

        # Payload indexes keep filtered searches fast; re-issuing is a no-op
        for field in ("metadata.doc_id", "metadata.user_id"):
            client.create_payload_index(
                collection_name=settings.DOCS_COLLECTION,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
        _collection_ready = True
    except Exception as e:
        logger.error("Could not prepare Qdrant collection %s: %s",
                     settings.DOCS_COLLECTION, e)
        raise QdrantUnavailableError(
            f"Could not prepare Qdrant collection {settings.DOCS_COLLECTION}: {e}"
        ) from e


def get_docs_store(embeddings: Embeddings) -> QdrantVectorStore:
    """
    Get a vector store handle for the documents collection.

    Reuses the shared client instead of building a new connection per query.
    The embeddings model is required so queries can be embedded at search time.

    Args:
        embeddings: Embeddings model used to embed query texts.

    Returns:
        A QdrantVectorStore bound to the configured documents collection.
    """
    return QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=settings.DOCS_COLLECTION,
        embedding=embeddings,
    )
