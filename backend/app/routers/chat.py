from fastapi import APIRouter

router = APIRouter()


@router.post("/", summary="Chat with the RAG assistant")
async def chat_placeholder():
    return {"message": "Chat endpoint coming soon"}