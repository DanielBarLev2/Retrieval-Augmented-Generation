"""
Pydantic models for ingestion-related endpoints.
"""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class WikipediaIngestRequest(BaseModel):
    """
    Request schema for triggering a Wikipedia ingestion run.
    """

    topics: List[str] = Field(
        ...,
        min_length=1,
        description="One or more search topics to ingest from Wikipedia.",
    )
    max_pages_per_topic: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum number of pages to fetch for each topic.",
    )
    language: str = Field(
        "en",
        pattern="^[a-z]{2}$",
        description="Two-letter Wikipedia language edition to target.",
    )
    chunk_size: int = Field(
        400,
        ge=100,
        le=2000,
        description="Target number of tokens (approximate words) in each chunk.",
    )
    chunk_overlap: int = Field(
        40,
        ge=0,
        le=400,
        description="Number of tokens to overlap between consecutive chunks.",
    )
    dry_run: bool = Field(
        False,
        description="If true, fetch and process pages but skip embedding/upsert.",
    )

    @field_validator("topics")
    @classmethod
    def strip_topics(cls, topics: List[str], info: ValidationInfo) -> List[str]:
        stripped = [topic.strip() for topic in topics if topic.strip()]
        if not stripped:
            raise ValueError("At least one non-empty topic must be provided.")
        return stripped


class WikipediaIngestResponse(BaseModel):
    """
    Summary payload returned after ingestion completes.
    """

    topics: List[str]
    processed_pages: int
    embedded_chunks: int
    skipped_pages: int = 0
    dry_run: bool = False


class WikipediaUrlIngestRequest(BaseModel):
    """
    Request schema for ingesting explicit Wikipedia page URLs.
    """

    urls: List[str] = Field(
        ...,
        min_length=1,
        description="One or more concrete Wikipedia page URLs to ingest.",
    )
    language: str = Field(
        "en",
        pattern="^[a-z]{2}$",
        description="Two-letter Wikipedia language edition to target.",
    )
    chunk_size: int = Field(
        400,
        ge=100,
        le=2000,
        description="Target number of tokens (approximate words) in each chunk.",
    )
    chunk_overlap: int = Field(
        40,
        ge=0,
        le=400,
        description="Number of tokens to overlap between consecutive chunks.",
    )
    dry_run: bool = Field(
        False,
        description="If true, fetch and process pages but skip embedding/upsert.",
    )

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, urls: List[str]) -> List[str]:
        cleaned = [url.strip() for url in urls if url and url.strip()]
        if not cleaned:
            raise ValueError("At least one valid Wikipedia URL must be provided.")
        return cleaned


class KnowledgeReference(BaseModel):
    """
    Summary of an article stored in the knowledge base.
    """

    page_id: int = Field(..., description="Wikipedia page identifier.")
    title: str | None = Field(None, description="Title of the ingested article.")
    topic: str | None = Field(None, description="Topic associated with the article.")
    url: str | None = Field(None, description="Source URL for the article.")
    chunk_count: int = Field(0, ge=0, description="Number of embedded chunks for the article.")