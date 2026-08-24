"""
Provider-agnostic chat model factory.

Exposes a module-level `llm` so existing call sites only change their import.
"""

import logging

from langchain_core.language_models.chat_models import BaseChatModel

from src.core.config import settings

logger = logging.getLogger(__name__)


class UnsupportedLLMProviderError(Exception):
    """Raised when LLM_PROVIDER names an unknown backend."""


def get_llm() -> BaseChatModel:
    """
    Build the configured chat model (temperature 0 for deterministic routing).

    Returns:
        A LangChain chat model for settings.LLM_PROVIDER.

    Raises:
        UnsupportedLLMProviderError: On unknown provider values.
    """
    provider = (settings.LLM_PROVIDER or "").lower()

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)

    if provider == "huggingface":
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        endpoint = HuggingFaceEndpoint(
            repo_id=settings.HF_LLM_MODEL,
            task="text-generation",
            max_new_tokens=512,
            huggingfacehub_api_token=settings.HF_API_TOKEN,
        )
        return ChatHuggingFace(llm=endpoint, temperature=0)

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=settings.OLLAMA_MODEL, temperature=0)

    raise UnsupportedLLMProviderError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")


def get_structured_output_kwargs() -> dict:
    """
    Extra kwargs for with_structured_output, honoring STRUCTURED_OUTPUT_METHOD.

    Returns:
        Dict such as {"method": "json_mode"}, or empty for library defaults.
    """
    return (
        {"method": settings.STRUCTURED_OUTPUT_METHOD}
        if settings.STRUCTURED_OUTPUT_METHOD
        else {}
    )


llm = get_llm()
logger.info(
    "Chat model ready: provider=%s model=%s",
    settings.LLM_PROVIDER,
    getattr(llm, "model_name", getattr(llm, "modelName", "?")),
)
