"""
Document ingestion pipeline: validate, load, chunk, embed, persist, register.
"""

import hashlib
import logging
import os
import tempfile
from uuid import uuid4

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymongo.errors import DuplicateKeyError

from src.db.document_registry import (
    RegistryUnavailableError,
    find_duplicate,
    register_document,
    serialize,
)
from src.db.qdrant_client import QdrantUnavailableError
from src.rag.retriever_setup import delete_doc_vectors, upsert_chunks
from src.tools.common_tools import enhance_description_with_llm

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MAX_DESCRIPTION_CHARS = 300
SUPPORTED_EXTENSIONS = (".pdf", ".txt")


class UnsupportedFileTypeError(Exception):
    """Raised for file types other than PDF and TXT."""


class DuplicateDocumentError(Exception):
    """Raised when identical content was already uploaded by the same user."""


class IngestionError(Exception):
    """Raised when chunking, embedding, upserting or registering fails."""


def _load_documents(filename: str, content: bytes) -> list:
    """
    Load PDF/TXT bytes into LangChain documents via a temp file.

    Args:
        filename: Original filename; extension selects the loader.
        content: Raw file bytes.

    Returns:
        List of loaded LangChain documents.

    Raises:
        UnsupportedFileTypeError: On unsupported extensions.
        IngestionError: If the file cannot be parsed.
    """
    extension = os.path.splitext(filename)[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError("Only PDF and TXT files are supported")

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=extension
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        loader = (
            PyPDFLoader(tmp_path)
            if extension == ".pdf"
            else TextLoader(tmp_path, encoding="utf-8")
        )
        return loader.load()
    except Exception as e:
        raise IngestionError(f"Error loading file: {e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def ingest_document(
    *,
    user_id: str,
    filename: str,
    raw_description: str,
    content: bytes,
) -> dict:
    """
    Process an uploaded file into Qdrant and the document registry.

    Ordering guarantee: vectors are written before the registry row (a row
    always implies a searchable, listed document); if registration fails,
    the just-written vectors are removed.

    Args:
        user_id: Owning user.
        filename: Original filename (stored as chunk source).
        raw_description: User-provided description.
        content: Raw file bytes.

    Returns:
        The serialized registry record.

    Raises:
        UnsupportedFileTypeError: If the file type is not PDF or TXT.
        DuplicateDocumentError: If identical content was already uploaded.
        IngestionError: If any processing step fails.
    """
    content_sha256 = hashlib.sha256(content).hexdigest()

    duplicate = find_duplicate(user_id, content_sha256)
    if duplicate:
        raise DuplicateDocumentError(
            f"Identical content was already uploaded as doc_id="
            f"{duplicate['doc_id']}"
        )

    docs = _load_documents(filename, content)

    description_enhanced = enhance_description_with_llm(
        raw_description[:MAX_DESCRIPTION_CHARS]
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    if not chunks:
        raise IngestionError("No extractable text found in the uploaded file")

    # Rebuild metadata explicitly: loader defaults would persist the temp
    # file path as source.
    doc_id = uuid4().hex
    for chunk in chunks:
        chunk.metadata = {
            "doc_id": doc_id,
            "user_id": user_id,
            "source": filename,
            "page": chunk.metadata.get("page"),
            "description": description_enhanced,
        }

    try:
        upsert_chunks(chunks)
    except QdrantUnavailableError as e:
        raise IngestionError(str(e)) from e

    try:
        record = register_document(
            doc_id=doc_id,
            user_id=user_id,
            filename=filename,
            description_raw=raw_description,
            description_enhanced=description_enhanced,
            content_sha256=content_sha256,
            num_chunks=len(chunks),
        )
    except DuplicateKeyError:
        # Raced another upload of identical content
        delete_doc_vectors(doc_id, user_id)
        raise DuplicateDocumentError(
            f"Identical content was already uploaded as doc_id={doc_id}"
        )
    except RegistryUnavailableError as e:
        # Compensate: without a registry row the doc must not stay searchable
        delete_doc_vectors(doc_id, user_id)
        raise IngestionError(str(e)) from e

    logger.info("Ingested doc %s (%s chunks) for user %s",
                doc_id, len(chunks), user_id)
    return serialize(record)
