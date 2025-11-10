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

