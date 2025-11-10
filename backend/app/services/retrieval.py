"""
Tools for embedding user queries and retrieving the closest chunks from Qdrant.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from app.core.settings import get_settings
from app.db.qdrant import get_qdrant_client
from app.embeddings.model import embed_query


@dataclass(slots=True)
class RetrievedChunk:
    """
    Lightweight representation of a chunk returned from Qdrant search.
    """

    id: str
    score: float
    payload: dict[str, Any]
    vector: list[float] | None = None

    @classmethod
    def from_scored_point(cls, point: rest.ScoredPoint) -> "RetrievedChunk":
        payload = dict(point.payload or {})
        vector = list(point.vector) if point.vector is not None else None
        return cls(
            id=str(point.id),
            score=float(point.score),
            payload=payload,
            vector=vector,
        )


class QueryRetriever:
    """
    Embed a natural language query and fetch the top matches from Qdrant.
    """

    def __init__(self, *, qdrant_client: QdrantClient | None = None):
        self.settings = get_settings()
        self.qdrant = qdrant_client or get_qdrant_client()

    @staticmethod
    def _validate_query(query: str) -> str:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("Query text must be non-empty.")
        return cleaned

    def embed(self, query: str) -> list[float]:
        """
        Turn the incoming query into a normalized vector.
        """
        cleaned = self._validate_query(query)
        return embed_query(cleaned)

    def search(
        self,
        query: str,
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        with_vectors: bool = False,
    ) -> list[RetrievedChunk]:
        """
        Embed the query and perform a nearest-neighbour search in Qdrant.
        """
        if limit < 1:
            raise ValueError("Search limit must be at least 1.")

        vector = self.embed(query)
        results = self.qdrant.search(
            collection_name=self.settings.collection_name,
            query_vector=vector,
            limit=limit,
            with_payload=True,
            with_vectors=with_vectors,
            score_threshold=score_threshold,
        )
        return [RetrievedChunk.from_scored_point(point) for point in results]

    def search_with_vector(
        self,
        vector: list[float],
        *,
        limit: int = 5,
        score_threshold: float | None = None,
        with_vectors: bool = False,
    ) -> list[RetrievedChunk]:
        """
        Variant of search that accepts a pre-computed query embedding.
        """
        if limit < 1:
            raise ValueError("Search limit must be at least 1.")

        results = self.qdrant.search(
            collection_name=self.settings.collection_name,
            query_vector=vector,
            limit=limit,
            with_payload=True,
            with_vectors=with_vectors,
            score_threshold=score_threshold,
        )
        return [RetrievedChunk.from_scored_point(point) for point in results]

