from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from starlette import status

from app.core.settings import get_settings
from app.db.qdrant import get_qdrant_client
from app.models import KnowledgeReference
from qdrant_client.http import models as rest

router = APIRouter()


@router.get(
    "/references",
    summary="List ingested knowledge base references.",
    response_model=List[KnowledgeReference],
)
async def list_references() -> List[KnowledgeReference]:
    settings = get_settings()
    client = get_qdrant_client()

    def _collect() -> List[Dict[str, Any]]:
        references: Dict[int, Dict[str, Any]] = {}
        offset = None

        while True:
            points, next_offset = client.scroll(
                collection_name=settings.collection_name,
                limit=256,
                with_payload=True,
                with_vectors=False,
                offset=offset,
            )
            if not points:
                break

            for point in points:
                payload = point.payload or {}
                page_id = payload.get("page_id")
                if page_id is None:
                    continue

                reference = references.get(page_id)
                if reference is None:
                    reference = {
                        "page_id": page_id,
                        "title": payload.get("title"),
                        "topic": payload.get("topic"),
                        "url": payload.get("url"),
                        "chunk_count": 0,
                    }
                    references[page_id] = reference

                reference["chunk_count"] += 1

            if next_offset is None:
                break

            offset = next_offset

        return sorted(
            references.values(),
            key=lambda ref: (str(ref.get("title") or "")).lower(),
        )

    raw_references = await run_in_threadpool(_collect)
    return [KnowledgeReference(**reference) for reference in raw_references]


@router.delete(
    "/references/{page_id}",
    summary="Remove an article from the knowledge base.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_reference(page_id: int) -> Response:
    settings = get_settings()
    client = get_qdrant_client()

    filter_ = rest.Filter(
        must=[
            rest.FieldCondition(
                key="page_id",
                match=rest.MatchValue(value=page_id),
            )
        ]
    )

    def _count() -> int:
        result = client.count(
            collection_name=settings.collection_name,
            exact=True,
            filter=filter_,
        )
        return result.count

    existing = await run_in_threadpool(_count)
    if existing == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference not found.")

    def _delete() -> None:
        client.delete(
            collection_name=settings.collection_name,
            points_selector=rest.FilterSelector(filter=filter_),
            wait=True,
        )

    await run_in_threadpool(_delete)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


