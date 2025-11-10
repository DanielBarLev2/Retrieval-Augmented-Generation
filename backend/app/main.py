from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.routers import health
from app.routers import chat
from app.routers import ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: initialize Mongo and Qdrant clients here later
    yield
    # TODO: close clients here when added


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

    @app.get("/")
    async def root():
        return {"message": "RAG backend is running"}

    return app


app = create_app()