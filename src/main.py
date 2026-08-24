"""
Main FastAPI application entry point.
"""

from fastapi import FastAPI, HTTPException

from src.api.routes import router

app = FastAPI(title="Adaptive RAG API")
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {"message": "Adaptive RAG API is running"}


@app.get("/health")
async def health():
    """
    Health probe for dependent services (Qdrant + MongoDB).

    Returns:
        Per-dependency status; raises 503 when anything is down.
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
        raise HTTPException(status_code=503, detail=status)
    return {"status": "ok", **status}
