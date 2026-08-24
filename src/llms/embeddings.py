"""
Provider-agnostic embeddings factory.

Default is a local HuggingFace sentence-transformer: free, offline, no rate
limits, reliable for multi-chunk ingestion bursts. The vector dimension is
always probed at runtime in retriever_setup, so switching models only
requires re-ingesting documents into a fresh Qdrant collection (never mix
embedding providers across ingested documents).
"""

import logging

from langchain_core.embeddings import Embeddings

from src.core.config import settings

logger = logging.getLogger(__name__)


class UnsupportedEmbeddingsProviderError(Exception):
    """Raised when EMBEDDINGS_PROVIDER names an unknown backend."""


def get_embeddings() -> Embeddings:
    """
    Build the configured embeddings instance.

    Returns:
        A LangChain Embeddings instance.

    Raises:
        UnsupportedEmbeddingsProviderError: On unknown or misconfigured values.
    """
    provider = (settings.EMBEDDINGS_PROVIDER or "").lower()

    if provider == "huggingface_local":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

    if provider == "huggingface_api":
        from langchain_community.embeddings import (
            HuggingFaceInferenceAPIEmbeddings,
        )
        if not settings.HF_API_TOKEN:
            raise UnsupportedEmbeddingsProviderError(
                "EMBEDDINGS_PROVIDER=huggingface_api requires "
                "HUGGINGFACEHUB_API_TOKEN"
            )
        return HuggingFaceInferenceAPIEmbeddings(
            api_key=settings.HF_API_TOKEN,
            model_name=settings.EMBEDDING_MODEL,
        )

    if provider == "groq_openai_compat":
        # Experimental: Groq exposes an OpenAI-compatible embeddings endpoint
        # (nomic-embed-text-v1_5) that is not prominently documented upstream;
        # verify availability before relying on it.
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL or "nomic-embed-text-v1.5",
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            chunk_size=128,
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)

    raise UnsupportedEmbeddingsProviderError(
        f"Unknown EMBEDDINGS_PROVIDER: {settings.EMBEDDINGS_PROVIDER}"
    )


embeddings = get_embeddings()
logger.info(
    "Embeddings ready: provider=%s model=%s",
    settings.EMBEDDINGS_PROVIDER,
    settings.EMBEDDING_MODEL,
)
