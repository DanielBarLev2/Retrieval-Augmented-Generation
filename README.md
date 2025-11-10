# Retrieval-Augmented-Generation

Local Retrieval-Augmented Generation (RAG) chat app for portfolio. Backend: FastAPI. Frontend: React. Uses Qdrant for vector search and MongoDB for chat history. Supports on-demand ingestion of topics from Wikipedia.

---

## Backend Quickstart

```bash
cd backend
conda create -n RAG python=3.11
conda activate RAG
pip install -r requirements.txt
```

Copy `.env.example` to `.env` (or set env vars manually). Key configuration values:

- `QDRANT_URL` / `QDRANT_API_KEY`
- `EMBED_MODEL` (defaults to `sentence-transformers/bge-small-en-v1.5`; override with `BAAI/bge-small-en-v1.5` while the former is unavailable)
- `MONGODB_URI`

Start the dependencies:

```bash
docker run -p 6333:6333 qdrant/qdrant:latest
docker run -p 27017:27017 mongo:7
```

Run the API:

```bash
cd backend
uvicorn app.main:app --reload
```

When the server is ready, FastAPI docs are available at `http://127.0.0.1:8000/docs`.

---

## Wikipedia Ingestion Endpoint

`POST /ingest/wikipedia`

Request body example:

```json
{
  "topics": ["neural network"],
  "max_pages_per_topic": 1,
  "chunk_size": 350,
  "chunk_overlap": 50,
  "dry_run": false
}
```

- `topics` — list of Wikipedia search queries.
- `dry_run` — if `true`, fetch/chunk/embed but skip Qdrant upsert (useful for smoke tests).
- `chunk_size`/`chunk_overlap` — controls whitespace-based splitting window.
- `language` — optional ISO code (default `en`).

The response summarises the ingestion run:

```json
{
  "topics": ["neural network"],
  "processed_pages": 1,
  "embedded_chunks": 3,
  "skipped_pages": 0,
  "dry_run": true
}
```

### Dry-run from PowerShell

```powershell
$payload = @{
  topics = @("neural network")
  max_pages_per_topic = 1
  chunk_size = 350
  chunk_overlap = 50
  dry_run = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/ingest/wikipedia" `
  -Method POST `
  -ContentType "application/json" `
  -Body $payload
```

### Full ingestion

Set `dry_run` to `false` to persist embeddings:

```powershell
$payload = @{
  topics = @("neural network", "graph theory")
  max_pages_per_topic = 2
  chunk_size = 400
  chunk_overlap = 40
  dry_run = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/ingest/wikipedia" `
  -Method POST `
  -ContentType "application/json" `
  -Body $payload
```

### Troubleshooting

- **422** → request JSON invalid. Validate schema in docs or use `ConvertTo-Json`.
- **502** → upstream fetch/embedding failure. Common causes: no outbound internet, Wikipedia 403/429 (set `topics` or add `User-Agent`), or missing embedding model. Override the model name with `EMBED_MODEL=BAAI/bge-small-en-v1.5` if the default ID is unavailable.
- Check uvicorn logs for full stack traces.

---

## Qdrant Verification

After ingestion, confirm points exist:

```bash
curl http://127.0.0.1:6333/collections/wiki_rag
curl -X POST http://127.0.0.1:6333/collections/wiki_rag/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 3}'
```

Payloads include `topic`, `title`, `url`, and `chunk_index`, allowing the chat endpoint to retrieve contextual passages.

