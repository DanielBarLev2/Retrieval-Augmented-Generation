"""
A single source for all environment config keeps credentials, URLs, and model names organized.
"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "RAG Backend"
    api_version: str = "0.1.0"
    frontend_origin: str = "http://localhost:5173"

    mongodb_uri: str = Field("mongodb://localhost:27017", alias="MONGODB_URI")
    mongodb_database: str = Field("rag_portfolio", alias="MONGODB_DATABASE")
    mongodb_messages_collection: str = Field("messages", alias="MONGODB_MESSAGES_COLLECTION")
    mongodb_server_selection_timeout_ms: int = Field(5000, alias="MONGODB_SERVER_SELECTION_TIMEOUT_MS")
    
    qdrant_url: str = Field("http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")

    collection_name: str = Field("wiki_rag", alias="COLLECTION_NAME")
    vector_size: int = Field(384, alias="VECTOR_SIZE")

    embed_model: str = Field("sentence-transformers/bge-small-en-v1.5", alias="EMBED_MODEL")
    ollama_host: str = Field("http://localhost:11434", alias="OLLAMA_HOST")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    return Settings()