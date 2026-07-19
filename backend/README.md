# SANJEEVANI — Backend

FastAPI backend for the SANJEEVANI industrial knowledge-intelligence platform
(ET AI Hackathon, PS8). This is the **step-1 scaffold**: structure + database
connections only. Feature files are stubs — see the docstring in each.

## What's wired up
- **FastAPI + Uvicorn** API with CORS for the Next.js frontend (`localhost:3000`)
- **Neo4j AuraDB** — knowledge graph (`app/db/neo4j_client.py`)
- **Qdrant** (Docker) — vector store (`app/db/qdrant_client.py`)
- **Neon Postgres** via SQLAlchemy — structured data (`app/db/postgres.py`)
- `GET /health` pings all three databases in one call

## Prerequisites
- Python **3.11**
- Docker (for Qdrant)
- `ffmpeg` on PATH (needed later by Whisper; not required for `/health`)

## 1. Create & activate a virtualenv

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```
> Note: `docling` and `openai-whisper` are large (pull in torch); first install
> takes a while.

## 3. Start Qdrant (Docker)

```bash
docker run -p 6333:6333 qdrant/qdrant
```
Leave it running in its own terminal. Dashboard: http://localhost:6333/dashboard

## 4. Configure secrets

```bash
cp .env.example .env    # Windows: copy .env.example .env
```
Then fill in `.env`:
- `OPENAI_API_KEY` — from platform.openai.com
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` — from the Neo4j AuraDB console
- `DATABASE_URL` — from the Neon dashboard (keep `?sslmode=require`)
- `QDRANT_URL` — leave as `http://localhost:6333`

## 5. Run the API

```bash
uvicorn app.main:app --reload
```
API docs: http://localhost:8000/docs

## 6. Verify all connections

```bash
curl http://localhost:8000/health
```
Expected when everything is green:
```json
{"status":"ok","neo4j":"ok","qdrant":"ok","postgres":"ok"}
```
Any DB that isn't reachable shows `"error: <reason>"` and `status` becomes
`"degraded"` — use that message to fix the specific connection.

## Project layout
```
backend/
  app/
    main.py            # FastAPI entry, CORS, health router
    config.py          # .env loading/validation (pydantic-settings)
    db/                # neo4j_client, qdrant_client, postgres (singletons + ping)
    models/            # SQLAlchemy model stubs (User, Equipment, WorkOrder, ...)
    ingestion/         # per-filetype ingester stubs (pdf, docx, excel, email, image, pid)
    services/          # embeddings, llm, whisper_service stubs
    routers/           # health (live); ingestion, copilot, equipment (stubs)
  requirements.txt
  .env.example
  README.md
```
