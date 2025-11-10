import logging
import requests
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.models import (
    WikipediaIngestRequest,
    WikipediaIngestResponse,
    WikipediaUrlIngestRequest,
)
from app.services import WikipediaIngestor

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/wikipedia",
            summary="Trigger Wikipedia ingestion",
            response_model=WikipediaIngestResponse)
async def ingest_wikipedia(request: WikipediaIngestRequest) -> WikipediaIngestResponse:
    ingestor = WikipediaIngestor()
    try:
        result = await run_in_threadpool(ingestor.run, request)
    except requests.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Wikipedia API returned an error.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("Unexpected failure during Wikipedia ingestion")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to ingest Wikipedia content: {exc}",
        ) from exc

    return result


@router.post(
    "/wikipedia/by-url",
    summary="Ingest specific Wikipedia URLs",
    response_model=WikipediaIngestResponse,
)
async def ingest_wikipedia_by_url(request: WikipediaUrlIngestRequest) -> WikipediaIngestResponse:
    ingestor = WikipediaIngestor()
    try:
        result = await run_in_threadpool(ingestor.run_from_urls, request)
    except requests.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Wikipedia API returned an error.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("Unexpected failure during Wikipedia URL ingestion")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to ingest Wikipedia content: {exc}",
        ) from exc

    return result