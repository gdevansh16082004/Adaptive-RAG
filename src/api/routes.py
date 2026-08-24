"""
API routes for RAG operations.
"""

import asyncio
import logging

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from langchain_core.messages import AIMessage, HumanMessage

from src.db.document_registry import (
    RegistryUnavailableError,
    delete_document,
    get_document,
    list_documents,
)
from src.db.qdrant_client import QdrantUnavailableError
from src.memory.chat_history_mongo import ChatHistory
from src.models.query_request import QueryRequest
from src.rag.document_upload import (
    DuplicateDocumentError,
    IngestionError,
    UnsupportedFileTypeError,
    ingest_document,
)
from src.rag.graph_builder import builder
from src.rag.retriever_setup import count_doc_vectors, delete_doc_vectors

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/rag/query")
async def rag_query(req: QueryRequest):
    """
    Process a RAG query and return the result.

    Args:
        req: The query request containing query text, session_id and user_id.

    Returns:
        The generated response from the RAG pipeline.
    """
    chat_history = ChatHistory.get_session_history(req.session_id)
    await chat_history.add_message(HumanMessage(content=req.query))

    # Fetch full history
    messages = await chat_history.get_messages()

    # builder.invoke is synchronous and performs network I/O (LLM, Qdrant,
    # Mongo); run it in a worker thread so the event loop is not blocked.
    result = await asyncio.to_thread(
        builder.invoke,
        {"messages": messages, "user_id": req.user_id},
    )

    output_message = result["messages"][-1]

    # Save assistant message
    await chat_history.add_message(AIMessage(content=output_message.content))

    return {"result": output_message}


@router.post("/rag/documents/upload")
async def upload_file(
    file: UploadFile = File(...),
    description: str = Form("", alias="description"),
    description_header: str | None = Header(None, alias="X-Description"),
    user_id: str = Header(..., alias="X-User-ID"),
):
    """
    Upload a document for RAG processing on behalf of a user.

    Args:
        file: The file to upload (PDF or TXT).
        description: Document description from the form body (preferred —
            free text doesn't survive HTTP header constraints).
        description_header: Legacy fallback used by the Streamlit client.
        user_id: Document owner provided via header.

    Returns:
        Upload status and the stored document record.

    Raises:
        HTTPException: 400 unsupported type, 409 duplicate content,
            503 storage/backend unavailable.
    """
    content = await file.read()
    raw_description = (description or description_header or "").strip()
    if not raw_description:
        raise HTTPException(
            status_code=400,
            detail="Missing description: provide a 'description' form field.",
        )
    try:
        document = await asyncio.to_thread(
            ingest_document,
            user_id=user_id,
            filename=file.filename,
            raw_description=raw_description,
            content=content,
        )
    except DuplicateDocumentError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IngestionError as e:
        logger.exception("Upload failed for user %s", user_id)
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected upload failure for user %s", user_id)
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "uploaded", "document": document}


@router.get("/rag/documents")
async def get_documents(user_id: str = Header(..., alias="X-User-ID")):
    """
    List the requesting user's registered documents.

    Args:
        user_id: Document owner provided via header.

    Returns:
        Documents owned by the user.
    """
    try:
        documents = list_documents(user_id)
    except RegistryUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"documents": documents}


@router.delete("/rag/documents/{doc_id}")
async def remove_document(
    doc_id: str,
    user_id: str = Header(..., alias="X-User-ID"),
):
    """
    Delete a document and its vectors from Qdrant.

    The registry row is removed first so subsequent queries cannot select
    the document even if vector deletion fails afterwards. A mismatching
    owner yields 404 without leaking the document's existence.

    Args:
        doc_id: ID of the document to delete.
        user_id: Requesting owner provided via header.

    Returns:
        Deletion summary including the number of vectors removed.

    Raises:
        HTTPException: 404 unknown document or wrong owner, 503 Qdrant down.
    """
    try:
        document = get_document(doc_id)
    except RegistryUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if document is None or document["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        chunks_deleted = count_doc_vectors(doc_id)
    except QdrantUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    delete_document(doc_id)

    vectors_removed = True
    try:
        delete_doc_vectors(doc_id, user_id)
    except QdrantUnavailableError as e:
        # Registry tombstone already prevents future use; surface partial failure
        logger.error("Vector cleanup failed for doc %s: %s", doc_id, e)
        vectors_removed = False

    return {
        "deleted": True,
        "doc_id": doc_id,
        "chunks_deleted": chunks_deleted,
        "vectors_removed": vectors_removed,
    }
