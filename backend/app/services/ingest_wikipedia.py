"""
Utilities to fetch, clean, chunk, embed, and upsert Wikipedia content.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence
from urllib.parse import unquote, urlparse

import requests
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from app.core.settings import get_settings
from app.db.qdrant import get_qdrant_client
from app.embeddings.model import embed_documents
from app.models import (
    WikipediaIngestRequest,
    WikipediaIngestResponse,
    WikipediaUrlIngestRequest,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WikiPage:
    """
    Lightweight container for the minimal Wikipedia page information we ingest.
    """

    page_id: int
    title: str
    url: str
    content: str
    topic: str


class WikipediaFetcher:
    """
    Wrapper around the MediaWiki API for retrieving page content.
    """

    API_TEMPLATE = "https://{language}.wikipedia.org/w/api.php"

    def __init__(self, *, language: str, session: requests.Session | None = None):
        self.language = language
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )

    def search(self, topic: str, *, limit: int) -> list[WikiPage]:
        """
        Fetch up to `limit` pages matching the topic. Returns cleaned page objects.
        """
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",
            "gsrsearch": topic,
            "gsrlimit": limit,
            "prop": "extracts|info",
            "explaintext": "1",
            "exsectionformat": "plain",
            "redirects": "1",
            "inprop": "url",
        }
        response = self.session.get(
            self.API_TEMPLATE.format(language=self.language),
            params=params,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", [])
        if not pages:
            logger.info("No pages found for topic '%s'", topic)
            return []

        # Sort results based on relevance (`index`) to keep deterministic ordering.
        pages.sort(key=lambda page: page.get("index", 0))

        results: list[WikiPage] = []
        for raw_page in pages:
            extract = raw_page.get("extract") or ""
            cleaned = _clean_text(extract)
            if not cleaned:
                logger.debug(
                    "Skipping page %s (%s) due to empty cleaned content",
                    raw_page.get("title"),
                    raw_page.get("pageid"),
                )
                continue

            results.append(
                WikiPage(
                    page_id=int(raw_page["pageid"]),
                    title=raw_page["title"],
                    url=raw_page.get("fullurl", ""),
                    content=cleaned,
                    topic=topic,
                )
            )
        return results

    def fetch_single_page(self, title: str, *, topic: str | None = None) -> WikiPage | None:
        """
        Fetch a single page by title using the search API for consistency.
        """
        pages = self.search(title, limit=1)
        if not pages:
            return None

        page = pages[0]
        if topic is not None:
            page.topic = topic
        return page


def _clean_text(text: str) -> str:
    """
    Normalize raw extracts: remove citation markers, trim whitespace, compress newlines.
    """
    if not text:
        return ""

    without_refs = re.sub(r"\[\d+]", "", text)
    condensed_newlines = re.sub(r"\n{3,}", "\n\n", without_refs)
    stripped = condensed_newlines.strip()
    return stripped


def _chunk_text(content: str, *, chunk_size: int, overlap: int) -> list[str]:
    """
    Split text into overlapping chunks using whitespace tokenization.
    """
    words = content.split()
    if not words:
        return []

    if overlap >= chunk_size:
        raise ValueError("Chunk overlap must be smaller than chunk size.")

    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            break
        chunk = " ".join(chunk_words)
        chunks.append(chunk)
    return chunks


def _build_points(
    page: WikiPage,
    *,
    chunks: Sequence[str],
    embeddings: Sequence[Sequence[float]],
) -> list[rest.PointStruct]:
    """
    Convert chunk embeddings into Qdrant point payloads.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("Number of embeddings must match number of chunks.")

    points: list[rest.PointStruct] = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        payload = {
            "source": "wikipedia",
            "topic": page.topic,
            "title": page.title,
            "url": page.url,
            "chunk_index": idx,
            "word_count": len(chunk.split()),
            "page_id": page.page_id,
            "content": chunk,
        }
        # Generate a stable UUID from page_id and chunk index
        import uuid
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{page.page_id}:{idx}"))
        points.append(
            rest.PointStruct(
                id=point_id,
                vector=list(embedding),
                payload=payload,
            )
        )
    return points


class WikipediaIngestor:
    """
    Orchestrates fetching, chunking, embedding, and upserting Wikipedia pages.
    """

    def __init__(
        self,
        *,
        qdrant_client: QdrantClient | None = None,
    ):
        self.settings = get_settings()
        self.fetcher: WikipediaFetcher | None = None
        self.qdrant = qdrant_client or get_qdrant_client()

    def run(self, request: WikipediaIngestRequest) -> WikipediaIngestResponse:
        """
        Execute the ingestion pipeline and return summary stats.
        """
        logger.info(
            "Starting Wikipedia ingestion for topics=%s dry_run=%s",
            request.topics,
            request.dry_run,
        )

        self.fetcher = WikipediaFetcher(language=request.language)
        processed_pages = 0
        embedded_chunks = 0
        skipped_pages = 0

        processed_topics: list[str] = []
        for topic in request.topics:
            pages = self.fetcher.search(topic, limit=request.max_pages_per_topic)
            if not pages:
                logger.warning("No pages found for topic '%s'", topic)
                continue

            topic_processed, topic_embedded, topic_skipped = self._process_pages(
                pages,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                dry_run=request.dry_run,
            )
            if topic_processed or topic_embedded:
                processed_topics.append(topic)

            processed_pages += topic_processed
            embedded_chunks += topic_embedded
            skipped_pages += topic_skipped

        logger.info(
            "Finished Wikipedia ingestion processed_pages=%s embedded_chunks=%s skipped_pages=%s dry_run=%s",
            processed_pages,
            embedded_chunks,
            skipped_pages,
            request.dry_run,
        )

        return WikipediaIngestResponse(
            topics=processed_topics or request.topics,
            processed_pages=processed_pages,
            embedded_chunks=embedded_chunks,
            skipped_pages=skipped_pages,
            dry_run=request.dry_run,
        )

    def run_from_urls(self, request: WikipediaUrlIngestRequest) -> WikipediaIngestResponse:
        """
        Execute the ingestion pipeline for explicit Wikipedia URLs.
        """
        logger.info(
            "Starting Wikipedia URL ingestion urls=%s dry_run=%s",
            request.urls,
            request.dry_run,
        )

        self.fetcher = WikipediaFetcher(language=request.language)
        processed_pages = 0
        embedded_chunks = 0
        skipped_pages = 0
        processed_identifiers: list[str] = []

        for url in request.urls:
            title = _title_from_url(url)
            if title is None:
                logger.warning("Unable to determine Wikipedia title from URL '%s'; skipping", url)
                continue

            page = self.fetcher.fetch_single_page(title, topic=title)
            if page is None:
                logger.warning("No page found for Wikipedia URL '%s'", url)
                continue

            page_processed, page_embedded, page_skipped = self._process_pages(
                [page],
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                dry_run=request.dry_run,
            )

            if page_processed:
                processed_identifiers.append(page.title)

            processed_pages += page_processed
            embedded_chunks += page_embedded
            skipped_pages += page_skipped

        logger.info(
            "Finished Wikipedia URL ingestion processed_pages=%s embedded_chunks=%s skipped_pages=%s dry_run=%s",
            processed_pages,
            embedded_chunks,
            skipped_pages,
            request.dry_run,
        )

        return WikipediaIngestResponse(
            topics=processed_identifiers or request.urls,
            processed_pages=processed_pages,
            embedded_chunks=embedded_chunks,
            skipped_pages=skipped_pages,
            dry_run=request.dry_run,
        )

    def _upsert_points(self, points: Iterable[rest.PointStruct]) -> None:
        """
        Upsert prepared points into Qdrant.
        """
        points = list(points)
        if not points:
            return

        self.qdrant.upsert(
            collection_name=self.settings.collection_name,
            wait=True,
            points=points,
        )

    def _process_pages(
        self,
        pages: Iterable[WikiPage],
        *,
        chunk_size: int,
        chunk_overlap: int,
        dry_run: bool,
    ) -> tuple[int, int, int]:
        processed_pages = 0
        embedded_chunks = 0
        skipped_pages = 0

        for page in pages:
            chunks = _chunk_text(
                page.content,
                chunk_size=chunk_size,
                overlap=chunk_overlap,
            )
            if not chunks:
                skipped_pages += 1
                logger.debug(
                    "No chunks produced for page %s (%s); skipping",
                    page.title,
                    page.page_id,
                )
                continue

            embeddings = embed_documents(chunks)
            embedded_chunks += len(chunks)
            processed_pages += 1

            if dry_run:
                continue

            points = _build_points(page, chunks=chunks, embeddings=embeddings)
            self._upsert_points(points)

        return processed_pages, embedded_chunks, skipped_pages


def _title_from_url(url: str) -> str | None:
    """
    Extract the Wikipedia page title from a canonical article URL.
    """
    parsed = urlparse(url)
    if "wikipedia.org" not in parsed.netloc:
        raise ValueError(f"URL '{url}' does not appear to be a Wikipedia link.")

    path = parsed.path.rstrip("/")
    if not path:
        return None

    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return None

    return unquote(segments[-1]).replace("_", " ")

