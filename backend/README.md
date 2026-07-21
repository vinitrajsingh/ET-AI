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
  tests/               # smoke tests (see below)
  requirements.txt
  .env.example
  README.md
```

## Ingestion (Phase 2)

The pipeline runs six stages per file: extract text -> entities -> relationships
-> MERGE into Neo4j -> chunk -> embed into Qdrant. It never duplicates a node
(everything MERGEs on a stable key defined in `app/db/schema.py`).

### Endpoints
```bash
# ingest one file
curl -F "file=@data/corpus_full/workorders/BharatPetrochem_Unit2_WorkOrders.xlsx" \
     http://localhost:8000/ingest

# seed the whole corpus (data/corpus_full)
curl -X POST http://localhost:8000/ingest/bulk
```
Both return a JSON summary (entities found, nodes created vs merged, chunks embedded).

### Verify in Neo4j Browser
List each equipment with its linked work-order count:
```cypher
MATCH (e:Equipment)
OPTIONAL MATCH (e)-[:HAS_WORKORDER]->(w:WorkOrder)
RETURN e.tag AS equipment, count(w) AS work_orders
ORDER BY equipment;
```
See the T-205 near-miss link:
```cypher
MATCH (e:Equipment {tag:'T-205'})-[:HAS_INCIDENT]->(i:Incident) RETURN e.tag, i.id;
```

### Verify in Qdrant
```bash
curl http://localhost:6333/collections/sanjeevani_chunks   # points_count = chunks stored
```

### Verify the whole graph at once
```bash
python -m scripts.verify_graph      # runs a set of read-only checks and prints them
```
Raw Cypher for the Neo4j Browser is in `scripts/verify.cypher`.

### Asset register (manual / regulation links)
Generic OEM manuals and OISD/Factory Act PDFs never name plant tags, so they can't
auto-link to equipment. `data/asset_register.json` declares which manual and which
regulations apply to each asset, and the connector MERGEs those edges:
```
Equipment -[:HAS_MANUAL]->  Document   (e.g. P-101  -> Grundfos manual)
Equipment -[:GOVERNED_BY]-> Document   (e.g. T-205  -> OISD-STD-105/106/116)
```
`POST /ingest/bulk` applies it automatically after ingestion. To (re)apply on its own:
```bash
python -c "from app.ingestion.asset_register import link_asset_register; print(link_asset_register())"
```

### Tests
```bash
# offline (no DB / no API cost): extractors + table entity extraction
pytest tests/test_text_extraction.py tests/test_entity_extraction.py -q

# live (needs Neo4j resumed, Qdrant up, OpenAI key): MERGE idempotency + end-to-end
pytest tests/test_graph_merge.py tests/test_pipeline.py -q

# everything
pytest -q
```

### Notes
- `docling` and `openai-whisper` are in `requirements.txt` but are heavy (torch).
  Phase-2 PDF extraction uses **PyMuPDF**; Docling is imported lazily for OCR and
  is optional. Whisper is only needed later (Guru Mode).
- P&ID tags come reliably from the drawing **filename**; the vision model (gpt-4o)
  enriches the description when `USE_PID_VISION=true`.
- Large real regulation/manual/incident PDFs contain no plant tags. Direct entity
  linkage still comes from the work-order sheet and P&IDs; the **asset register**
  (above) supplies the curated manual/regulation-to-equipment edges on top.
