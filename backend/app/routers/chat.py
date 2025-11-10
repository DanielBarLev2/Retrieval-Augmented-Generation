from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Iterable
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.core.settings import get_settings
from app.db.mongo import get_messages_collection
from app.models import ChatRequest, ChatResponse, ChatSource
from app.services import ChatTurn, OllamaClient, PromptBuilder, QueryRetriever, RetrievedChunk

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
    created_at = datetime.now(timezone.utc)

    user_document = {
        "session_id": session_id,
        "role": "user",
        "content": request.message,
        "sources": [],
        "created_at": created_at,
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
        "created_at": datetime.now(timezone.utc),
    }
    await _insert_messages([user_document, assistant_document])

    return ChatResponse(
        session_id=session_id,
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        created_at=assistant_document["created_at"],
    )