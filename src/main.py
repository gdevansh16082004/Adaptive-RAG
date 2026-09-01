"""
Main FastAPI application entry point.
"""

from fastapi import FastAPI

from src.api.routes import router
from src.models.api_response import APIResponse, ErrorDetail

app = FastAPI(title="Adaptive RAG API")
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return APIResponse(data={"message": "Adaptive RAG API is running"})


@app.get("/health")
async def health():
    """
    Health probe for dependent services (Qdrant + MongoDB).

    Returns:
        Per-dependency status; structured error when anything is down.
    """
    status = {"qdrant": "ok", "mongo": "ok"}
    healthy = True

    try:
        from src.db.qdrant_client import get_qdrant_client
        get_qdrant_client().get_collections()
    except Exception:
        status["qdrant"] = "unavailable"
        healthy = False

    try:
        from pymongo import MongoClient

        from src.core.config import settings
        MongoClient(
            settings.MONGODB_URL, serverSelectionTimeoutMS=2000
        ).admin.command("ping")
    except Exception:
        status["mongo"] = "unavailable"
        healthy = False

    if not healthy:
        return APIResponse(
            success=False,
            data=status,
            error=ErrorDetail(
                code="service_degraded",
                message="One or more backend services are unavailable.",
            ),
        )
    return APIResponse(data={"status": "ok", **status})
