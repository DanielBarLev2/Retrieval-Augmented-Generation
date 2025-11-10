from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.db import (
    close_mongo_client,
    close_qdrant_client,
    ensure_collection,
    ensure_indexes,
    get_mongo_client,
    get_qdrant_client,
    verify_connection,
)
from app.routers import chat
from app.routers import health
from app.routers import ingest
from app.routers import knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_client = get_mongo_client()
    verify_connection(mongo_client)
    ensure_indexes(mongo_client)

    qdrant_client = get_qdrant_client()
    ensure_collection(qdrant_client)

    try:
        yield
    finally:
        close_mongo_client()
        close_qdrant_client()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
    app.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])

    @app.get("/")
    async def root():
        return {"message": "RAG backend is running"}

    return app


app = create_app()