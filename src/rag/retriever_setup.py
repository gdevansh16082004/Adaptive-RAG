"""
Retriever setup and Qdrant vector store configuration.

All chunks live in one shared Qdrant collection and are scoped at query time
by payload filters on metadata.user_id and metadata.doc_id. langchain-qdrant
nests Document.metadata under the payload key "metadata", hence the dotted
filter keys.
"""

import logging
from uuid import uuid4

from langchain_core.documents import Document
from langchain_core.tools import Tool, create_retriever_tool
from langchain_core.vectorstores import VectorStoreRetriever
from qdrant_client import models

from src.core.config import settings
from src.db.qdrant_client import (
    QdrantUnavailableError,
    ensure_docs_collection,
    get_docs_store,
    get_qdrant_client,
)
from src.llms.embeddings import embeddings

logger = logging.getLogger(__name__)


def upsert_chunks(chunks: list[Document]) -> list[str]:
    """
    Embed chunks (which must already carry doc metadata) and store them.

    Args:
        chunks: Chunked Documents with doc_id/user_id/source/description metadata.

    Returns:
        The point IDs stored in Qdrant.

    Raises:
        QdrantUnavailableError: If Qdrant cannot be reached.
    """
    dimension = len(embeddings.embed_query("dimension probe"))
    ensure_docs_collection(dimension)

    ids = [str(uuid4()) for _ in chunks]
    get_docs_store(embeddings).add_documents(chunks, ids=ids)
    logger.info("Upserted %s chunks into %s", len(chunks), settings.DOCS_COLLECTION)
    return ids


def build_scope_filter(user_id: str, doc_ids: list[str]) -> models.Filter:
    """
    Build a Qdrant filter restricting results to one user's documents.

    Args:
        user_id: Owner of the documents; always applied as a condition.
        doc_ids: Selected document IDs (capped at MAX_DOCS_PER_QUERY).

    Returns:
        A models.Filter combining the user_id and doc_id conditions.
    """
    must = [
        models.FieldCondition(
            key="metadata.user_id",
            match=models.MatchValue(value=user_id),
        )
    ]
    if doc_ids:
        must.append(
            models.FieldCondition(
                key="metadata.doc_id",
                match=models.MatchAny(
                    any=doc_ids[: settings.MAX_DOCS_PER_QUERY]
                ),
            )
        )
    return models.Filter(must=must)


def build_retriever(
    user_id: str,
    doc_ids: list[str],
    k: int | None = None,
) -> VectorStoreRetriever:
    """
    Build a retriever scoped to a user's selected documents.

    Args:
        user_id: Owner of the documents.
        doc_ids: Relevant document IDs chosen during classification.
        k: Number of chunks to fetch. Defaults to settings.RETRIEVER_K.

    Returns:
        A VectorStoreRetriever applying the scope filter on every search.
    """
    return get_docs_store(embeddings).as_retriever(
        search_kwargs={
            "k": k or settings.RETRIEVER_K,
            "filter": build_scope_filter(user_id, doc_ids),
        }
    )


def build_retriever_tool(retriever: VectorStoreRetriever, description: str) -> Tool:
    """
    Wrap a scoped retriever in a ReAct tool.

    Args:
        retriever: Retriever produced by build_retriever.
        description: Tool instruction describing the in-scope documents.

    Returns:
        A LangChain Tool usable by the ReAct agent.
    """
    return create_retriever_tool(
        retriever,
        "retriever_customer_uploaded_documents",
        f"{description}\nDon't use this tool to answer anything else.",
    )


def count_doc_vectors(doc_id: str) -> int:
    """
    Count points in Qdrant belonging to a document.

    Args:
        doc_id: Unique document identifier.

    Returns:
        Number of vectors stored for the document.

    Raises:
        QdrantUnavailableError: If Qdrant cannot be reached.
    """
    try:
        return get_qdrant_client().count(
            collection_name=settings.DOCS_COLLECTION,
            count_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.doc_id",
                        match=models.MatchValue(value=doc_id),
                    )
                ]
            ),
            exact=True,
        ).count
    except Exception as e:
        raise QdrantUnavailableError(f"Could not count vectors for {doc_id}: {e}") from e


def delete_doc_vectors(doc_id: str, user_id: str) -> None:
    """
    Delete every vector belonging to a document.

    Uses the raw client because QdrantVectorStore.delete() only accepts point
    IDs, while deletion here must work from payload filters. The owner id is
    included as defense-in-depth against cross-user deletes.

    Args:
        doc_id: Document whose vectors should be removed.
        user_id: Requesting owner.

    Raises:
        QdrantUnavailableError: If Qdrant cannot be reached.
    """
    try:
        result = get_qdrant_client().delete(
            collection_name=settings.DOCS_COLLECTION,
            points_selector=models.FilterSelector(
                filter=build_scope_filter(user_id, [doc_id])
            ),
        )
        logger.info("Deleted vectors for doc %s (status=%s)", doc_id, result.status)
    except Exception as e:
        raise QdrantUnavailableError(f"Could not delete vectors for {doc_id}: {e}") from e
