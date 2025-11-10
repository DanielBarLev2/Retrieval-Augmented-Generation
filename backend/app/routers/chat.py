from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any, Iterable, List
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from starlette import status

from app.core.settings import get_settings
from app.db.mongo import get_messages_collection, get_sessions_collection
from app.models import (
    ChatRequest,
    ChatResponse,
    ChatSessionMessages,
    ChatSessionSummary,
    ChatSessionUpdate,
    ChatSource,
    StoredChatMessage,
)
from app.services import ChatTurn, OllamaClient, PromptBuilder, QueryRetriever, RetrievedChunk
from pymongo import ReturnDocument

router = APIRouter()


def _build_sources(chunks: Iterable[RetrievedChunk]) -> list[ChatSource]:
    sources: list[ChatSource] = []
    for chunk in chunks:
        payload = chunk.payload
        sources.append(
            ChatSource(
                title=payload.get("title"),
                url=payload.get("url"),
                chunk_index=payload.get("chunk_index"),
                page_id=payload.get("page_id"),
                topic=payload.get("topic"),
                score=chunk.score,
            )
        )
    return sources


def _extract_contexts(chunks: Iterable[RetrievedChunk]) -> list[str]:
    contexts: list[str] = []
    for chunk in chunks:
        text = chunk.payload.get("content")
        if not text:
            continue
        contexts.append(text)
    return contexts


async def _insert_messages(documents: list[dict]) -> None:
    collection = get_messages_collection()

    def _bulk_insert():
        if not documents:
            return
        collection.insert_many(documents)

    await run_in_threadpool(_bulk_insert)


async def _ensure_session_metadata(session_id: str, created_at: datetime, default_title: str) -> None:
    collection = get_sessions_collection()

    def _upsert():
        collection.update_one(
            {"session_id": session_id},
            {
                "$setOnInsert": {
                    "session_id": session_id,
                    "title": default_title,
                    "created_at": created_at,
                }
            },
            upsert=True,
        )

    await run_in_threadpool(_upsert)


@router.get(
    "/sessions",
    summary="List stored chat sessions.",
    response_model=List[ChatSessionSummary],
)
async def list_sessions(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of sessions to return."),
) -> List[ChatSessionSummary]:
    collection = get_messages_collection()
    sessions_collection = get_sessions_collection()

    def _aggregate() -> List[dict[str, Any]]:
        pipeline = [
            {"$match": {"session_id": {"$type": "string"}}},
            {"$sort": {"created_at": 1}},
            {
                "$group": {
                    "_id": "$session_id",
                    "title": {"$first": "$content"},
                    "message_count": {"$sum": 1},
                    "last_message_at": {"$last": "$created_at"},
                    "last_message_role": {"$last": "$role"},
                    "last_message_preview": {"$last": "$content"},
                }
            },
            {"$sort": {"last_message_at": -1}},
            {"$limit": limit},
        ]
        return list(collection.aggregate(pipeline))

    documents = await run_in_threadpool(_aggregate)
    session_ids = [document.get("_id") for document in documents if isinstance(document.get("_id"), str)]

    def _load_metadata() -> dict[str, dict[str, Any]]:
        if not session_ids:
            return {}
        cursor = sessions_collection.find({"session_id": {"$in": session_ids}})
        metadata: dict[str, dict[str, Any]] = {}
        for document in cursor:
            session_id = document.get("session_id")
            if isinstance(session_id, str):
                metadata[session_id] = document
        return metadata

    try:
        metadata_map = await run_in_threadpool(_load_metadata)
    except Exception:  # pragma: no cover - defensive
        metadata_map = {}

    summaries: List[ChatSessionSummary] = []
    for document in documents:
        session_id = document.get("_id")
        if not isinstance(session_id, str):
            continue
        metadata = metadata_map.get(session_id, {})
        title = metadata.get("title") or "New Conversation"
        if not isinstance(title, str) or not title.strip():
            title = "New Conversation"

        last_message_at = document.get("last_message_at")
        if not isinstance(last_message_at, datetime):
            fallback_time = metadata.get("updated_at") or metadata.get("created_at")
            if isinstance(fallback_time, datetime):
                last_message_at = fallback_time
            else:
                last_message_at = datetime.fromtimestamp(0, tz=timezone.utc)

        last_message_preview = document.get("last_message_preview")
        if last_message_preview is None:
            last_message_preview = metadata.get("last_message_preview")
        if isinstance(last_message_preview, str):
            last_message_preview = last_message_preview.strip() or None
        else:
            last_message_preview = None

        summaries.append(
            ChatSessionSummary(
                session_id=session_id,
                title=title,
                message_count=document.get("message_count", 0),
                last_message_at=last_message_at,
                last_message_role=document.get("last_message_role"),
                last_message_preview=last_message_preview,
            )
        )

    return summaries


@router.get(
    "/sessions/{session_id}/messages",
    summary="Retrieve messages for a specific session.",
    response_model=ChatSessionMessages,
)
async def get_session_messages(session_id: str) -> ChatSessionMessages:
    collection = get_messages_collection()

    def _fetch() -> List[dict[str, Any]]:
        cursor = collection.find({"session_id": session_id}).sort(
            [("created_at", 1), ("_id", 1)]
        )
        return list(cursor)

    documents = await run_in_threadpool(_fetch)
    if not documents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    messages: list[StoredChatMessage] = []
    for document in documents:
        metadata = document.get("metadata") or {}
        sources_payload = document.get("sources") or []
        sources = [ChatSource(**source) for source in sources_payload]
        messages.append(
            StoredChatMessage(
                id=str(document.get("_id")),
                role=document.get("role"),
                content=document.get("content"),
                created_at=document.get("created_at"),
                sources=sources,
                latency_ms=metadata.get("latency_ms"),
            )
        )

    return ChatSessionMessages(session_id=session_id, messages=messages)


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a chat session and its messages.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(session_id: str) -> Response:
    collection = get_messages_collection()
    sessions_collection = get_sessions_collection()

    def _delete() -> int:
        result = collection.delete_many({"session_id": session_id})
        return result.deleted_count

    deleted = await run_in_threadpool(_delete)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    def _delete_metadata() -> None:
        sessions_collection.delete_one({"session_id": session_id})

    await run_in_threadpool(_delete_metadata)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/sessions/{session_id}",
    summary="Update chat session metadata.",
    response_model=ChatSessionSummary,
)
async def update_session(session_id: str, payload: ChatSessionUpdate) -> ChatSessionSummary:
    sessions_collection = get_sessions_collection()
    messages_collection = get_messages_collection()

    def _update() -> dict[str, Any] | None:
        result = sessions_collection.find_one_and_update(
            {"session_id": session_id},
            {
                "$set": {
                    "title": payload.title,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return result

    metadata = await run_in_threadpool(_update)

    if metadata is None:
        metadata = {
            "session_id": session_id,
            "title": payload.title,
        }

    def _last_message() -> dict[str, Any] | None:
        cursor = (
            messages_collection.find({"session_id": session_id})
            .sort("created_at", -1)
            .limit(1)
        )
        results = list(cursor)
        return results[0] if results else None

    last_message = await run_in_threadpool(_last_message)
    if last_message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    message_count = await run_in_threadpool(
        lambda: messages_collection.count_documents({"session_id": session_id})
    )

    return ChatSessionSummary(
        session_id=session_id,
        title=metadata.get("title"),
        message_count=message_count,
        last_message_at=last_message.get("created_at"),
        last_message_role=last_message.get("role"),
        last_message_preview=last_message.get("content"),
    )


@router.post(
    "/",
    summary="Chat with the RAG assistant",
    response_model=ChatResponse,
)
async def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()

    # Prepare helper services
    retriever = QueryRetriever()
    prompt_builder = PromptBuilder()

    # Retrieve contextual chunks (embedding runs in threadpool to avoid blocking the loop)
    try:
        retrieved_chunks = await run_in_threadpool(
            lambda: retriever.search(
                request.message,
                limit=request.top_k,
                with_vectors=False,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve relevant context.",
        ) from exc

    contexts = _extract_contexts(retrieved_chunks)
    sources = _build_sources(retrieved_chunks)

    history_turns = [
        ChatTurn(role=turn.role, content=turn.content) for turn in request.history
    ]

    prompt = prompt_builder.build_prompt(
        question=request.message,
        contexts=contexts,
        history=history_turns,
    )

    model_name = request.model or settings.ollama_model
    options = {}
    if request.temperature is not None:
        options["temperature"] = request.temperature

    start_time = perf_counter()

    try:
        async with OllamaClient() as client:
            generation = await client.generate(
                model=model_name,
                prompt=prompt,
                options=options or None,
            )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned an error: {exc.response.text}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Failed to reach Ollama service.",
        ) from exc

    answer = generation.response.strip()
    if not answer:
        answer = "I'm sorry, I wasn't able to generate a response."

    latency_ms = (perf_counter() - start_time) * 1000.0

    session_id = request.session_id or str(uuid4())
    user_created_at = datetime.now(timezone.utc)
    # Ensure assistant timestamp is after user timestamp
    assistant_created_at = user_created_at + timedelta(microseconds=1)

    user_document = {
        "session_id": session_id,
        "role": "user",
        "content": request.message,
        "sources": [],
        "created_at": user_created_at,
    }
    assistant_document = {
        "session_id": session_id,
        "role": "assistant",
        "content": answer,
        "sources": [source.model_dump() for source in sources],
        "metadata": {
            "model": model_name,
            "latency_ms": latency_ms,
            "retrieved": len(sources),
        },
        "created_at": assistant_created_at,
    }
    await _insert_messages([user_document, assistant_document])
    await _ensure_session_metadata(
        session_id=session_id,
        created_at=assistant_document["created_at"],
        default_title="New Conversation",
    )

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        created_at=assistant_document["created_at"],
    )