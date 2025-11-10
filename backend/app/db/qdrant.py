"""
Helpers for interacting with the Qdrant vector database and ensuring the collection exists.
"""
from __future__ import annotations

from functools import lru_cache
from typing import cast

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def _client() -> QdrantClient:
    """
    Create a cached Qdrant client.

    The client holds on to an underlying HTTP session, so caching the instance keeps
    connection reuse cheap while still exposing a single point where we can close it.
    """
    settings = get_settings()
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


def get_qdrant_client() -> QdrantClient:
    """Return the cached Qdrant client."""
    return _client()


def close_qdrant_client() -> None:
    """Close the cached Qdrant client and clear the cache."""
    client = _client()
    client.close()
    _client.cache_clear()


def _resolve_vector_params(
    vectors_config: rest.VectorParams | rest.VectorParamsMap,
) -> rest.VectorParams:
    """
    Qdrant supports either a single VectorParams object or a map when using named vectors.
    This helper normalizes both cases to a VectorParams instance.
    """
    if isinstance(vectors_config, rest.VectorParams):
        return vectors_config

    # Named vector collections return a map. We only expect a single entry in our setup.
    if len(vectors_config) != 1:
        raise ValueError(
            "Expected a single vector configuration in Qdrant collection but found "
            f"{len(vectors_config)}."
        )
    return cast(rest.VectorParams, next(iter(vectors_config.values())))


def ensure_collection(client: QdrantClient | None = None) -> None:
    """
    Ensure the target collection exists with the expected vector size and metric.

    If the collection is missing it will be created; if it already exists we verify the
    configuration to guard against silent mismatches that would cause runtime errors.
    """
    settings = get_settings()
    collection_name = settings.collection_name
    expected_vector_size = settings.vector_size

    client = client or get_qdrant_client()

    if client.has_collection(collection_name):
        info = client.get_collection(collection_name)
        params = _resolve_vector_params(info.config.params.vectors_config)

        if params.size != expected_vector_size:
            raise ValueError(
                "Existing Qdrant collection does not match configured vector size: "
                f"expected {expected_vector_size}, found {params.size}."
            )
        if params.distance != rest.Distance.COSINE:
            raise ValueError(
                "Existing Qdrant collection is using an unexpected distance metric: "
                f"{params.distance}. Expected COSINE."
            )
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=rest.VectorParams(
            size=expected_vector_size,
            distance=rest.Distance.COSINE,
        ),
    )

