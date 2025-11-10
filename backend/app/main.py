from fastapi import FastAPI

from app.routers import health


def create_app() -> FastAPI:
    app = FastAPI(title="RAG Backend", version="0.1.0")
    app.include_router(health.router)

    @app.get("/")
    async def root():
        return {"message": "RAG backend is running"}

    return app


app = create_app()

