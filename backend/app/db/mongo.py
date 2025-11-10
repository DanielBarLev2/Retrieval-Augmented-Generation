"""
Utilities for configuring and accessing the MongoDB deployment backing chat history.
"""
from __future__ import annotations
from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def _client() -> MongoClient:
    """
    Lazily build a single MongoClient for the process.

    MongoClient pools connections internally and is safe to reuse across threads.
    Using an lru_cache keeps the implementation simple while giving us an easy
    hook for cleaning up during application shutdown.
    """
    settings = get_settings()
    return MongoClient(settings.mongodb_uri,
                       uuidRepresentation="standard",
                       serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms)


def get_mongo_client() -> MongoClient:
    """Return the shared MongoClient instance."""
    return _client()


def close_mongo_client() -> None:
    """Close the cached MongoClient and clear the cache."""
    client = _client()
    client.close()
    _client.cache_clear()


def get_database(client: MongoClient | None = None) -> Database:
    """Return the primary application database."""
    client = client or get_mongo_client()
    settings = get_settings()
    return client[settings.mongodb_database]


def get_messages_collection(client: MongoClient | None = None) -> Collection:
    """Return the collection used to persist chat messages."""
    settings = get_settings()
    database = get_database(client)
    return database[settings.mongodb_messages_collection]


def ensure_indexes(client: MongoClient | None = None) -> None:
    """
    Create the indexes that the chat flow relies on.

    Index builds in MongoDB are idempotent, so running this on every boot is safe.
    """
    collection = get_messages_collection(client)
    collection.create_index("session_id", name="session_id_idx")
    collection.create_index([("created_at", -1)], name="created_at_desc_idx")


def verify_connection(client: MongoClient | None = None) -> None:
    """
    Perform a lightweight connection check.

    Calling this during startup surfaces misconfiguration early instead of failing
    later during a request.
    """
    client = client or get_mongo_client()
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:  # pragma: no cover - defensive
        raise ConnectionError(
            "Unable to connect to MongoDB with the configured URI."
        ) from exc

