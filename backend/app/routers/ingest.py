import requests
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.models import WikipediaIngestRequest, WikipediaIngestResponse
from app.services import WikipediaIngestor

router = APIRouter()


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
        raise HTTPException(
            status_code=502,
            detail="Failed to ingest Wikipedia content.",
        ) from exc

    return result