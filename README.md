# SANJEEVANI — The Plant's Living Brain

**ET AI Hackathon 2026 · Problem Statement 8**  
**Team:** Vipers  
**Repo:** [github.com/vinitrajsingh/ET-AI](https://www.github.com/vinitrajsingh/ET-AI)

> Every plant has the answers buried in its documents. SANJEEVANI is the brain that remembers everything, connects everything, and speaks up before disaster — even with the voice of engineers who retired years ago.

---

## What it is

SANJEEVANI is an **HSE-first industrial knowledge system** for a fictional refinery — **Bharat Petrochem Unit-2**. It ingests decades of plant documents once, remembers them as an equipment-centric knowledge graph, and then:

- answers field questions with citations (**Expert Copilot**)
- predicts failures before anyone asks (**Predictive Maintenance**)
- blocks unsafe work with real cited history (**AI Intervention Engine**)
- preserves retiring engineers' voice notes (**Guru Mode**)
- turns weeks of audit prep into seconds (**Audit Package**)

### Core design decision

Most teams build a chatbot over documents (plain RAG). SANJEEVANI is built differently: the centre is not a pile of PDFs — it is the **equipment** (pumps, tanks, boilers). Every document, incident, and repair attaches to the machine it is about. That merge-on-equipment graph is the product.

We call the retrieval style **Hybrid GraphRAG**: exact facts from Neo4j + meaning-based passages from Qdrant, handed to an LLM that is instructed to refuse when it does not know.

---

## Three layers

| Layer | Role | What ships |
|---|---|---|
| **Knowledge** | Get documents in | Ingestion → entity extraction → Neo4j MERGE → Qdrant embeddings |
| **Intelligence** | Reason over knowledge | Equipment 360, Copilot, Prediction, Guru Mode, HSE Compliance |
| **Action** | Turn insight into work | Permit interventions, work-order drafts, one-click audit PDF |

---

## Six product flows

1. **Ingestion** — Upload PDF / Excel / P&ID / email → extract text → LLM entities → MERGE into Neo4j (P-101 stays one node) → chunk + embed into Qdrant.
2. **Expert Copilot** — Technician asks about P-101 → hybrid retrieval (graph subgraph + vector chunks) → cited answer, optional guru quote by name.
3. **Prediction** — Interval stats on work-order history (not a black-box model) → risk card on Equipment 360 → optional human-approved work-order draft.
4. **AI Intervention** — Raise Hot Work on T-205 → deterministic graph checks → near-miss + OISD-105 warnings → mandatory acknowledgments → audit trail.
5. **Guru Mode** — Voice/text note → structured symptom / meaning / action → linked forever to equipment + engineer name.
6. **Compliance & Audit** — Map regulations to evidence → fleet compliance board → generate audit PDF in seconds.

---

## Roles (MVP)

A top-right **role switcher** (no auth in v1) changes the menu:

| Role | Primary screens |
|---|---|
| Field Technician | Copilot, Equipment |
| Engineer / Supervisor | Equipment 360, Permits, Copilot |
| HSE Officer | Compliance, Permits, Audit |
| Admin | Ingestion, Guru Mode, Equipment |

---

## Demo plant & seeded corpus

**Plant:** Bharat Petrochem Unit-2  
**Assets tracked:** P-101 (crude feed pump), C-201 (recycle gas compressor), T-205 (naphtha storage tank), HX-301 (heat exchanger), B-7 (steam boiler)

The MVP corpus is already seeded under `backend/data/corpus_full/`. Sources:

| Folder | What we seeded | Source |
|---|---|---|
| `regulations/` | OISD-STD-105, OISD-STD-106, OISD-STD-116, Factories Act 1948 | Oil Industry Safety Directorate (OISD); Government of India |
| `incidents/` | CSB investigation / safety study PDFs | [U.S. Chemical Safety Board](https://www.csb.gov) (public domain) |
| `manuals/` | Grundfos pump, Atlas Copco compressor, Forbes Marshall boiler manuals | Manufacturer product literature |
| `pid/` | Unit-2 P&ID drawings tagged to P-101, C-201, T-205, HX-301, B-7 | Public P&ID image datasets (Zenodo / similar), renamed to plant tags |
| `workorders/` | `BharatPetrochem_Unit2_WorkOrders.xlsx` | **Custom demo work orders we authored** for Unit-2 — tags, failure modes, and bearing replacement dates crafted so predictive maintenance demos cleanly |

Also included:

- `backend/data/asset_register.json` — curated manual / regulation → equipment links  
- `backend/data/compliance_rules.json` — HSE compliance rules used by the compliance agent  

---

## Tech stack

| Piece | Choice |
|---|---|
| Frontend | Next.js + Tailwind CSS |
| Backend | FastAPI (Python 3.11) + Uvicorn |
| Knowledge graph | Neo4j AuraDB |
| Vector store | Qdrant (Docker) |
| Structured data | Neon Postgres |
| LLM / embeddings | OpenAI API |
| Voice (Guru) | Whisper (optional; text notes work without it) |

---

## Prerequisites

- Python **3.11**
- Node.js **18+**
- Docker (for Qdrant)
- Accounts / keys: OpenAI, Neo4j AuraDB, Neon Postgres

---

## Run locally

### 1. Clone

```bash
git clone https://github.com/vinitrajsingh/ET-AI.git
cd ET-AI
```

### 2. Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

Dashboard: http://localhost:6333/dashboard

### 3. Backend

```bash
cd backend
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
```

Fill in `.env`:

| Variable | Where from |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Neo4j Aura console |
| `DATABASE_URL` | Neon dashboard (`?sslmode=require`) |
| `QDRANT_URL` | leave `http://localhost:6333` |

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health → expect `{"status":"ok","neo4j":"ok","qdrant":"ok","postgres":"ok"}`

**Seed the graph (first time):**

- UI: open the app as **Admin** → **Ingestion** → **Seed corpus**, or  
- API: `POST http://localhost:8000/ingest/bulk`

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Suggested demo path

1. **Admin → Ingestion** — confirm DB health green; seed corpus if needed.  
2. **Equipment** — open **P-101** → Equipment 360 (timeline, prediction, documents).  
3. **Copilot** — ask: *“P-101 vibration is high, what should I check?”*  
4. **Prediction** — expand evidence on P-101; create / approve a work-order draft.  
5. **Permits** — raise **Hot Work** on **T-205** → acknowledge intervention cards.  
6. **Guru Mode** — capture a note (e.g. Rajesh Kumar / whistling bearing).  
7. **Compliance → Audit** — review gaps; download the audit PDF.

---

## Design notes (for judges)

- **Equipment-centric, not document-centric** — MERGE on tag; no duplicate P-101 nodes.  
- **Predictions are interval statistics** with clickable work-order evidence — not an opaque ML score.  
- **Permit interventions are deterministic** (graph facts + rules), so they cannot hallucinate danger.  
- **HSE means H + S + E** — compliance covers Health, Safety, and Environment.  
- **Industry-agnostic engine** — only the corpus is refinery-specific; the same stack works for steel, cement, pharma, etc.

---

## Project layout

```
ET-AI/
├── backend/                 # FastAPI app
│   ├── app/                 # routers, services, ingestion, db clients
│   ├── data/
│   │   ├── corpus_full/     # seeded regulations, incidents, manuals, P&IDs, work orders
│   │   ├── asset_register.json
│   │   └── compliance_rules.json
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Next.js UI
└── README.md
```

More backend detail: [`backend/README.md`](backend/README.md)

---

## License / usage

Hackathon MVP for educational demo use. Third-party PDFs remain under their original publishers' terms (OISD, CSB, OEM manuals, etc.).
