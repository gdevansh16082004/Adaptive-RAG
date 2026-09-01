"""
API routes for RAG operations.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from langchain_core.messages import AIMessage, HumanMessage
from sse_starlette.sse import EventSourceResponse

from src.db.document_registry import (
    RegistryUnavailableError,
    delete_document,
    get_document,
    list_documents,
)
from src.db.qdrant_client import QdrantUnavailableError
from src.memory.chat_history_mongo import ChatHistory
from src.models.api_response import APIResponse, ErrorDetail
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


def _error_response(status_code: int, code: str, message: str):
    """
    Raise an HTTPException whose body follows the APIResponse envelope.

    Args:
        status_code: HTTP status code.
        code: Machine-readable snake_case error slug.
        message: Human-readable explanation.

    Raises:
        HTTPException: Always raised with a structured detail dict.
    """
    body = APIResponse(
        success=False,
        error=ErrorDetail(code=code, message=message),
    )
    raise HTTPException(status_code=status_code, detail=body.model_dump())


@router.post("/rag/query", response_model=APIResponse)
async def rag_query(req: QueryRequest):
    """
    Process a RAG query and return the result.

    Args:
        req: The query request containing query text, session_id and user_id.

    Returns:
        APIResponse wrapping the generated answer.
    """
    chat_history = ChatHistory.get_session_history(req.session_id)
    await chat_history.add_message(HumanMessage(content=req.query))

    # Fetch full history
    messages = await chat_history.get_messages()

    try:
        # builder.invoke is synchronous and performs network I/O (LLM, Qdrant,
        # Mongo); run it in a worker thread so the event loop is not blocked.
        #
        # LangSmith metadata lets you filter traces by user/session in the
        # dashboard — no extra dependency needed (part of langchain_core).
        langsmith_config = {
            "metadata": {
                "user_id": req.user_id,
                "session_id": req.session_id,
            },
            "run_name": "adaptive_rag_query",
        }
        result = await asyncio.to_thread(
            builder.invoke,
            {"messages": messages, "user_id": req.user_id},
            config=langsmith_config,
        )
    except QdrantUnavailableError:
        logger.exception("Qdrant unavailable during query for user %s", req.user_id)
        _error_response(503, "qdrant_unavailable", "Vector store is temporarily unavailable.")
    except RegistryUnavailableError:
        logger.exception("Registry unavailable during query for user %s", req.user_id)
        _error_response(503, "registry_unavailable", "Document registry is temporarily unavailable.")
    except Exception:
        logger.exception("Graph execution failed for user %s", req.user_id)
        _error_response(500, "graph_execution_error", "An internal error occurred while processing your query.")

    output_message = result["messages"][-1]

    # Save assistant message
    await chat_history.add_message(AIMessage(content=output_message.content))

    # Preserve the shape the Streamlit client expects: data.result.content
    return APIResponse(data={"result": output_message})


@router.post("/rag/query/stream")
async def rag_query_stream(req: QueryRequest):
    """
    Process a RAG query and stream intermediate results via SSE.

    Streams events:
    - node: {"node": "query_analysis"} - node transition
    - token: {"content": "word"} - LLM token chunk
    - done: {"content": "full final answer"} - completion
    - error: {"code": "...", "message": "..."} - errors

    Args:
        req: The query request containing query text, session_id and user_id.

    Returns:
        EventSourceResponse with SSE stream.
    """
    chat_history = ChatHistory.get_session_history(req.session_id)
    await chat_history.add_message(HumanMessage(content=req.query))
    messages = await chat_history.get_messages()

    async def event_generator():
        try:
            langsmith_config = {
                "metadata": {
                    "user_id": req.user_id,
                    "session_id": req.session_id,
                },
                "run_name": "adaptive_rag_query_stream",
            }

            accumulated_content = ""
            sources = []
            last_generate_content = ""

            async for state_update in builder.astream(
                {"messages": messages, "user_id": req.user_id},
                config=langsmith_config,
                stream_mode="updates",
            ):
                # state_update is {node_name: state_dict}
                for node_name, node_state in state_update.items():
                    # Notify the frontend which node is active
                    yield {
                        "event": "node",
                        "data": json.dumps({"node": node_name}),
                    }

                    # Capture sources from retriever
                    if "sources" in node_state:
                        sources = node_state["sources"]

                    if node_name in ("generate", "general_llm"):
                        # Both nodes return messages.
                        # generate() returns {"messages": [AIMessage(...)]}
                        # general_llm() returns {"messages": AIMessage(...)}
                        raw = node_state.get("messages")
                        if raw is None:
                            continue
                        # Normalise: could be a single message or a list
                        if isinstance(raw, list):
                            last_msg = raw[-1] if raw else None
                        else:
                            last_msg = raw
                        if last_msg is None:
                            continue
                        content = (
                            last_msg.content
                            if hasattr(last_msg, "content")
                            else str(last_msg)
                        )

                        if node_name == "generate":
                            # Hold — only emit after verify passes
                            last_generate_content = content
                        else:
                            # general_llm has no verify — send immediately
                            accumulated_content = content
                            yield {
                                "event": "token",
                                "data": json.dumps({"content": content}),
                            }

                    elif node_name == "verify":
                        score = node_state.get("verify_score")
                        if score == "yes" and last_generate_content:
                            # Verification passed — send the answer
                            accumulated_content = last_generate_content
                            yield {
                                "event": "token",
                                "data": json.dumps({
                                    "content": last_generate_content,
                                }),
                            }
                            last_generate_content = ""
                        elif score != "yes":
                            # Verification failed — generate will re-run;
                            # discard the rejected answer
                            logger.info(
                                "Verification failed, will regenerate"
                            )
                            last_generate_content = ""

            # Edge case: graph ended without verify (e.g. search route
            # where verify returns yes immediately but the order means
            # content is still held, or verify node was skipped entirely)
            if last_generate_content and not accumulated_content:
                accumulated_content = last_generate_content
                yield {
                    "event": "token",
                    "data": json.dumps({
                        "content": last_generate_content,
                    }),
                }

            # Emit sources
            if sources:
                yield {
                    "event": "sources",
                    "data": json.dumps({"sources": sources}),
                }

            # Save assistant message to history
            if accumulated_content:
                await chat_history.add_message(
                    AIMessage(content=accumulated_content)
                )

            yield {
                "event": "done",
                "data": json.dumps({"done": True}),
            }

        except QdrantUnavailableError:
            logger.exception("Qdrant unavailable during stream for user %s", req.user_id)
            yield {
                "event": "error",
                "data": json.dumps({
                    "code": "qdrant_unavailable",
                    "message": "Vector store is temporarily unavailable."
                }),
            }
        except RegistryUnavailableError:
            logger.exception("Registry unavailable during stream for user %s", req.user_id)
            yield {
                "event": "error",
                "data": json.dumps({
                    "code": "registry_unavailable",
                    "message": "Document registry is temporarily unavailable."
                }),
            }
        except Exception:
            logger.exception("Graph streaming failed for user %s", req.user_id)
            yield {
                "event": "error",
                "data": json.dumps({
                    "code": "graph_execution_error",
                    "message": "An internal error occurred while processing your query."
                }),
            }

    return EventSourceResponse(event_generator())


@router.post("/rag/documents/upload", response_model=APIResponse)
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
        APIResponse wrapping the stored document record.
    """
    content = await file.read()
    raw_description = (description or description_header or "").strip()
    if not raw_description:
        _error_response(400, "missing_description", "Provide a 'description' form field.")

    try:
        document = await asyncio.to_thread(
            ingest_document,
            user_id=user_id,
            filename=file.filename,
            raw_description=raw_description,
            content=content,
        )
    except DuplicateDocumentError as e:
        _error_response(409, "duplicate_document", str(e))
    except UnsupportedFileTypeError as e:
        _error_response(400, "unsupported_file_type", str(e))
    except IngestionError as e:
        logger.exception("Upload failed for user %s", user_id)
        _error_response(503, "ingestion_error", str(e))
    except Exception as e:
        logger.exception("Unexpected upload failure for user %s", user_id)
        _error_response(500, "upload_error", str(e))

    return APIResponse(data={"status": "uploaded", "document": document})


@router.get("/rag/documents", response_model=APIResponse)
async def get_documents(user_id: str = Header(..., alias="X-User-ID")):
    """
    List the requesting user's registered documents.

    Args:
        user_id: Document owner provided via header.

    Returns:
        APIResponse wrapping the list of documents.
    """
    try:
        documents = list_documents(user_id)
    except RegistryUnavailableError as e:
        _error_response(503, "registry_unavailable", str(e))
    return APIResponse(data={"documents": documents})


@router.delete("/rag/documents/{doc_id}", response_model=APIResponse)
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
        APIResponse wrapping the deletion summary.
    """
    try:
        document = get_document(doc_id)
    except RegistryUnavailableError as e:
        _error_response(503, "registry_unavailable", str(e))

    if document is None or document["user_id"] != user_id:
        _error_response(404, "document_not_found", "Document not found.")

    try:
        chunks_deleted = count_doc_vectors(doc_id)
    except QdrantUnavailableError as e:
        _error_response(503, "qdrant_unavailable", str(e))

    delete_document(doc_id)

    vectors_removed = True
    try:
        delete_doc_vectors(doc_id, user_id)
    except QdrantUnavailableError as e:
        # Registry tombstone already prevents future use; surface partial failure
        logger.error("Vector cleanup failed for doc %s: %s", doc_id, e)
        vectors_removed = False

    return APIResponse(data={
        "deleted": True,
        "doc_id": doc_id,
        "chunks_deleted": chunks_deleted,
        "vectors_removed": vectors_removed,
    })
