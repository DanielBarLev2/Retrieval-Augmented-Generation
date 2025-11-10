from fastapi import APIRouter

router = APIRouter()


@router.post("/wikipedia", summary="Trigger Wikipedia ingestion")
async def ingest_placeholder():
    return {"message": "Ingestion endpoint coming soon"}