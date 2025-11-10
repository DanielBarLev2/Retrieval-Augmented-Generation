from fastapi.testclient import TestClient

from app.main import app
from app.services.ollama import OllamaGenerationResult
from app.services.retrieval import RetrievedChunk


def test_chat_endpoint_success(monkeypatch):
    fake_chunks = [
        RetrievedChunk(
            id="1:0",
            score=0.75,
            payload={
                "title": "Sample Page",
                "url": "https://example.com/sample",
                "chunk_index": 0,
                "page_id": 1,
                "topic": "testing",
                "content": "This is the chunk content used for testing.",
            },
            vector=None,
        )
    ]

    class FakeRetriever:
        def __init__(self):
            self.calls = []

        def search(self, query: str, *, limit: int, with_vectors: bool):
            self.calls.append((query, limit, with_vectors))
            return fake_chunks

    fake_retriever = FakeRetriever()
    monkeypatch.setattr("app.routers.chat.QueryRetriever", lambda: fake_retriever)

    class FakeCollection:
        def __init__(self):
            self.inserted = []

        def insert_many(self, documents):
            self.inserted.extend(documents)

    fake_collection = FakeCollection()
    monkeypatch.setattr("app.routers.chat.get_messages_collection", lambda: fake_collection)

    class FakeSessionsCollection:
        def __init__(self):
            self.upserts = []

        def update_one(self, filter_doc, update_doc, upsert=False):
            self.upserts.append((filter_doc, update_doc, upsert))

    fake_sessions_collection = FakeSessionsCollection()
    monkeypatch.setattr("app.routers.chat.get_sessions_collection", lambda: fake_sessions_collection)

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("app.routers.chat.run_in_threadpool", fake_run_in_threadpool)

    class FakeOllamaClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def generate(self, *, model, prompt, system_prompt=None, options=None):
            assert model == "llama3.2:3b"
            assert "Retrieved Context" in prompt
            return OllamaGenerationResult(
                model=model,
                response="Mock assistant answer.",
                done=True,
            )

    monkeypatch.setattr("app.routers.chat.OllamaClient", FakeOllamaClient)

    client = TestClient(app)

    response = client.post(
        "/chat/",
        json={"message": "Explain testing.", "top_k": 3},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Mock assistant answer."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["title"] == "Sample Page"
    assert data["session_id"]
    assert data["latency_ms"] >= 0.0

    # Retrieval called with expected parameters
    assert fake_retriever.calls == [("Explain testing.", 3, False)]

    # Messages persisted
    assert len(fake_collection.inserted) == 2
    assert fake_collection.inserted[0]["role"] == "user"
    assert fake_collection.inserted[1]["role"] == "assistant"

