"""
Core configuration and environment settings.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # ---- Model providers -------------------------------------------------
    # groq | openai | huggingface | ollama
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    HF_API_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN", "")
    HF_LLM_MODEL = os.getenv("HF_LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

    # huggingface_local | huggingface_api | groq_openai_compat | openai
    EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "huggingface_local")
    EMBEDDING_MODEL = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    # Leave empty for library default; set "json_mode" if a model chokes on
    # tool-based structured output.
    STRUCTURED_OUTPUT_METHOD = os.getenv("STRUCTURED_OUTPUT_METHOD", "")

    # ---- Services --------------------------------------------------------
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    CODE_COLLECTION = os.getenv("QDRANT_CODE_COLLECTION", "codebase")
    DOCS_COLLECTION = os.getenv("QDRANT_DOCS_COLLECTION", "documents")
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "adaptive_rag")

    # ---- Retrieval tuning ------------------------------------------------
    RETRIEVER_K = int(os.getenv("RETRIEVER_K", "4"))
    MAX_DOCS_PER_QUERY = int(os.getenv("MAX_DOCS_PER_QUERY", "20"))


settings = Settings()

# Set env variables for LangChain integrations
os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
