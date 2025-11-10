"""
Pydantic models for the chat endpoint.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ChatHistoryTurn(BaseModel):
    """
    Representation of a previous message in the conversation sent by either party.
    """

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("History message content must be non-empty.")
        return cleaned


class ChatSource(BaseModel):
    """
    Metadata about a context chunk returned to the frontend.
    """

    title: str | None = None
    url: str | None = None
    chunk_index: int | None = None
    score: float | None = None
    page_id: int | None = None
    topic: str | None = None


class ChatRequest(BaseModel):
    """
    Incoming payload for the /chat endpoint.
    """

    message: str = Field(..., min_length=1, description="User message to send to the assistant.")
    session_id: Optional[str] = Field(
        default=None,
        description="Identifier used to group chat history. A new one is generated if omitted.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of context chunks to retrieve from Qdrant.",
    )
    history: list[ChatHistoryTurn] = Field(
        default_factory=list,
        description="Conversation history leading up to the current message.",
    )
    model: Optional[str] = Field(
        default=None,
        description="Override the default Ollama model for this request.",
    )
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional sampling temperature override.",
    )

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message must be non-empty.")
        return cleaned


class ChatResponse(BaseModel):
    """
    Response returned by the /chat endpoint.
    """

    session_id: str
    answer: str
    sources: list[ChatSource]
    latency_ms: float
    created_at: datetime


