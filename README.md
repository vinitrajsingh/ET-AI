# SANJEEVANI — The Plant's Living Brain
### ET AI Hackathon 2.0 · Phase 2 Build Sprint · Problem Statement 8

> **One-line pitch:** *"Every plant has the answers buried in its documents. SANJEEVANI is the brain that remembers everything, connects everything, and speaks up before disaster — even with the voice of engineers who retired years ago."*

> **Positioning line:** The Industrial Operating System That Never Forgets — **an HSE-first safety intelligence brain** that also does maintenance and knowledge.

---

## 1. Problem Statement (PS 8)

**AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain**

The problem in simple words:
- A large industrial plant (plant = factory/facility, e.g., a refinery or steel plant) keeps its knowledge in **7–12 disconnected systems** — drawings in one place, maintenance records in another, safety procedures in a third, emails everywhere.
- This fragmentation causes **18–22% of unplanned downtime** and — more importantly — **it is a safety problem** (the PS says this word first).
- **25% of experienced engineers will retire within 10 years**, taking undocumented knowledge with them forever (the "knowledge cliff").

**Our job:** Build an AI platform that ingests all these heterogeneous documents and makes their collective intelligence queryable, actionable, and continuously updated.

---

## 2. Core Insight (Our Differentiator)

> **Don't build a chatbot over documents. Build a brain around equipment.**

Every other team will do: Documents → Embeddings → Chat (generic RAG).

We do: **Equipment → Knowledge → Reasoning → Prediction → Action.**

The center of our system is not documents — it's the **equipment itself**. Every pump, boiler, compressor gets a living profile (like a LinkedIn profile for machines). Documents are just the food; the knowledge graph is the brain.

**Second differentiator — HSE-first framing:** The hackathon maintainer hinted at HSE (Health, Safety, Environment). Judges will evaluate through a safety lens, not a "search efficiency" lens. Our headline story: *the system prevents the next fatality by remembering what everyone else forgot.* Efficiency is the bonus; safety is the headline.

---

## 3. What is HSE and Why It's Central

- **HSE = Health, Safety, Environment** — the department in every industrial company responsible for preventing worker injuries/fatalities, occupational health hazards, and environmental compliance.
- PS8 itself says: *"Knowledge fragmentation… is a safety problem, a quality problem, and an operational efficiency problem"* — safety comes first.
- Every document type PS8 mentions is an HSE document: safety procedures, inspection reports, incident/near-miss reports, OISD (Oil Industry **Safety** Directorate), Factory Act (worker safety law), PESO (explosives/hazardous substances), environmental norms.

**How we cover H, S, and E:**

| Letter | Covered by |
|---|---|
| **H** (Health) | Occupational hazard warnings in interventions (gas exposure, confined space) |
| **S** (Safety) | AI Intervention Engine, Lessons Learned, permit checks, OISD compliance |
| **E** (Environment) | CTO (Consent to Operate) conditions, CPCB emission norms, hazardous waste rules in the compliance agent — e.g., flag "stack emission test overdue per CTO condition 4.2" |

**Demo climax = HSE moment:** The hot-work-permit intervention scene (system recalls a 2023 near-miss + cites OISD-105 gas testing requirement) is the centerpiece of the demo, not the chatbot.

---

## 4. Final Locked Feature Scope

Organized in **3 layers** (this structure is also our architecture diagram and pitch narrative):

### Layer 1 — Knowledge (the foundation)
1. **Universal Document Ingestion** — Upload PDFs, scanned forms, P&ID drawings, spreadsheets, emails. Docling/OCR converts → LLM extracts entities (equipment tags, people, dates, failure modes, regulation clauses).
2. **Continuous Learning Knowledge Graph** — Neo4j graph that **merges** new facts into existing nodes (P-101 stays one node, gets richer) instead of duplicating. New relationships computed on every upload. Graph visibly grows live on screen.
3. **Vector Store** — Qdrant holds document chunks for semantic search (RAG).

### Layer 2 — Intelligence (the brain)
4. **Equipment 360 ("machine biography")** — Click any equipment tag → its entire life in one screen: drawing, failures, maintenance history, parts replaced, applicable regulations, people who worked on it, guru notes, health/risk card. Directly attacks the "7–12 disconnected systems" problem.
5. **Expert Copilot** — Chat with citations + confidence scores. Mobile-friendly for field technicians. Answers combine graph facts + manual chunks + guru wisdom (credited by name).
6. **Predictive Maintenance** — Background job computes failure/replacement intervals from work-order history. Example: *"P-101 bearings replaced at 18, 17, 19-month intervals; current bearing is 16 months old → ~81% probability of replacement needed within 30 days"* — with the three past work orders cited as clickable evidence. **The AI speaks first; nobody asked.** (Implementation secret: this is interval statistics, not deep ML — we control the synthetic dates, so a clean pattern is guaranteed.)
7. **Industrial Memory (Guru Mode)** — Retiring engineer records a casual voice note (Hindi/English) + optional photo: *"Pump P-101 ke bearing mein jab halki whistling sound aati hai, matlab 2 hafte mein fail hoga."* Whisper transcribes → LLM structures it → stored as a first-class graph node linked to equipment + engineer profile. Later, the copilot quotes the retired expert **by name**. This addresses the knowledge-cliff line in the PS that every other team will ignore.
8. **Lessons Learned Engine** — Mines incident/near-miss reports for recurring patterns invisible to individual reviews.
9. **HSE Compliance Intelligence** — Maps OISD / Factory Act / PESO / environmental (CTO, CPCB) requirements against current equipment states and inspection records; flags gaps with exact clause citations.

### Layer 3 — Action (the hands)
10. **AI Intervention Engine** (renamed from "Proactive Warnings") — When a new work permit is created (e.g., hot work on Tank T-205), the system checks the graph BEFORE the permit activates: past incidents on that equipment, near-misses, applicable OISD clauses, conflicting active permits. Shows a ⚠️ intervention card with a mandatory acknowledgment checklist. Every acknowledgment is logged → becomes audit evidence.
11. **Simulation-Lite** ("Can we postpone maintenance?") — Shows a **risk rating with the reasoning chain**: current age vs. historical failure intervals vs. OEM manual limits, with **explicit adjustable assumptions**. NOT fake precise numbers (no invented "₹11 lakh loss" — judges will ask where numbers came from).
12. **One-Click Outputs** — (a) "Generate Audit Package" → compliance evidence PDF in seconds; (b) "Create Work Order" → pre-filled draft from a prediction card, human approves.
13. **Executive Dashboard** (if time permits) — Risk scores, compliance %, upcoming maintenance, HSE view (active permits with risk flags, open safety observations, days since last incident).

### Explicitly CUT (and why)
- ❌ **Time Machine** (timeline slider of whole plant) — needs time-versioned graph state; demonstrates visualization, not intelligence. Prediction already covers "the future."
- ❌ **Full workflow automation engine** — replaced by the one-click work-order draft (same story, 5% of effort).
- ❌ **Video ingestion in Guru Mode** — voice + photo gives the identical demo moment; video adds days of work.
- ❌ **Fake precise money/risk numbers in simulation** — credibility killer.

---

## 5. Complete System Flow (6 Flows)

### Flow 1 — Document Ingestion (the feeding flow)
Upload file → Docling/OCR → LLM extracts entities → **Graph merge** (attach to existing P-101 node, compute new links) → parallel chunk+embed into Qdrant → graph grows live on screen → insight pass ("3rd bearing event on P-101 — prediction updated") → notification.

### Flow 2 — Asking a Question (Expert Copilot)
Technician on mobile: *"P-101 vibration is high, what should I check?"* → FastAPI → LangGraph agent → **hybrid retrieval** (Neo4j subgraph + Qdrant chunks) → answer with steps, citations (manual page, work order ID, incident report), confidence score, and guru note quoted by name → one tap to source doc or Equipment 360.

### Flow 3 — Prediction (AI speaks first)
Scheduled background job → scans work-order intervals per equipment → statistics → "81% probability within 30 days" card with clickable evidence → appears on Equipment 360 + dashboard + notification → **"Create work order draft"** button → human approves.

### Flow 4 — AI Intervention Engine (the HSE climax)
Supervisor creates hot work permit on T-205 → system queries graph around T-205 → finds 2023 near-miss (vent line not isolated) + OISD-105 gas-testing clause → ⚠️ intervention card with near-miss link + clause + required-precautions checklist → supervisor must acknowledge each item → acknowledgments logged as audit evidence.

### Flow 5 — Industrial Memory (Guru Mode)
Senior engineer selects equipment → records voice (Hindi/English) + optional photo → Whisper transcription → LLM structures (symptom, meaning, source: Rajesh Kumar, 25 yrs) → stored as graph node → surfaces forever in Flows 2 & 4, credited by name. (Notes submitted by regular users need **admin approval** before becoming trusted knowledge.)

### Flow 6 — Compliance & Audit (one-click)
Compliance agent continuously maps graph vs. regulations (OISD clauses per equipment, overdue inspections, unmet CTO environmental conditions) → dashboard shows compliance % + gap list with clause citations → **"Generate audit package"** → PDF with equipment list, inspection status, incident history, closed intervention checklists, gap register.

**Demo = Flows 1→2→3→4→5→6 in order.** One continuous story: documents in → lives protected → decisions out. Closing metric: *"Time-to-answer: 8 seconds vs 2–3 hours of manual searching."*

---

## 6. User Roles (Who Feeds the System)

| Role | Can do | Who feeds what |
|---|---|---|
| **Admin** (Document Controller / plant digitalization head) | Bulk upload, approve guru notes, manage users, generate audit package | **One-time bulk load** of existing corpus (manuals, P&IDs, regulations, historical work orders, incidents, email archives). In production this is automatic via connectors (SAP/Maximo, SharePoint/DMS, email) — "Uploads are for demo; production uses connectors." |
| **Engineer / Supervisor** (HSE officer, maintenance planner) | Create permits & work orders, file incident/near-miss reports, see predictions & interventions, full dashboard | **Daily ongoing feed as a side effect of normal work** — permits, closed work orders, incident reports enter the graph automatically. The system feeds itself. |
| **Field Technician** (mobile) | Ask copilot, close work orders with notes, view Equipment 360 | Closure notes enter the graph |
| **Guru** (a flag on any user; nominated by Admin/HSE manager — typically 20+ yrs experience or retiring soon) | Record voice/photo knowledge against equipment they know | Structured exit-knowledge program: HR flags retirements → engineers record in final months |

Prototype: a simple **role dropdown at login** is enough — but different screens per role make judges see a deployable product (feeds the UX score, 15%).

---

## 7. Data Strategy (Real Documents, Fictional Plant)

**Industry chosen: Oil & Gas / Refinery** — the only industry where every PS8 document type is publicly downloadable. (Automotive/pharma keep records private.)

**The fictional plant:** "Bharat Petrochem Unit-2" with ~15 equipment items (P-101 pump, C-201 compressor, T-205 tank, HX-301 heat exchanger, B-7 boiler, etc.)

**~80% real documents + 20% synthetic connecting layer:**

| Document type | Real source (free) | Use |
|---|---|---|
| Regulations | OISD-STD-105 (Work Permit System), OISD-106 (Pressure Relief), OISD-116 (Fire Protection); Factories Act 1948; PESO rules | Compliance agent |
| Incident reports | US Chemical Safety Board (csb.gov) full investigation PDFs; OISD safety alerts | Lessons Learned engine |
| OEM manuals | Grundfos/KSB pumps, Atlas Copco compressors, Siemens/ABB motors, Forbes Marshall boilers | Copilot citations |
| P&ID drawings | Zenodo public P&ID dataset; Roboflow P&ID symbol datasets | Drawing ingestion demo |
| Work orders | NIST Maintenance Work Order datasets; Kaggle work-order text datasets; awesome-industrial-datasets (GitHub) | Maintenance intelligence + prediction |
| Environmental | State PCB Consent to Operate (CTO) format, CPCB emission norms, hazardous waste rules | The "E" in HSE |
| Emails, guru notes, some work orders | **Synthetic** (we write them) | Connecting layer |

**The trick:** Rename equipment tags across all documents so everything refers to the same machines (find-and-replace weekend job). Ensure work-order dates create a clean interval pattern for the prediction demo. Result — the pitch line: *"Every document in this system is a real industrial document."*

---

## 8. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | **Next.js + Tailwind CSS** | Web app, mobile-responsive |
| Graph visualization | **Cytoscape.js** (or react-force-graph) | Live-growing knowledge graph, relationship explorer |
| Backend | **FastAPI** (Python) | API layer |
| Agent orchestration | **LangGraph** | Copilot, extraction, compliance, intervention agents |
| Knowledge graph | **Neo4j** | Equipment-centric entity graph, merge-on-upload |
| Vector DB | **Qdrant** (or Chroma) | RAG chunks |
| Structured data | **PostgreSQL** | Users, permits, work orders, notifications |
| Reasoning LLM | **Claude / GPT API** | Entity extraction, copilot answers, intervention reasoning |
| Embeddings | **BGE-M3 or OpenAI embeddings** | Semantic search |
| Document processing | **Docling** (preferred over raw Tesseract) + vision LLM for drawings | PDF/scan/spreadsheet ingestion |
| Voice | **Whisper API** | Guru Mode transcription (Hindi/English) |

---

## 9. Scalability Answer (for judges)

**The system design is industry-agnostic; only the data is industry-specific.** The engine (ingestion, graph, copilot, prediction, interventions, compliance) works for steel, power, cement, pharma, chemicals, mining. What changes is just the corpus fed in (regulations, manuals, incidents).

Pitch line: **"Built industry-agnostic, demonstrated on a refinery."** → answers the Scalability criterion (15%) directly.

---

## 10. Judging Criteria Mapping

| Criterion | Weight | Our answer |
|---|---|---|
| Innovation | 25% | Equipment-centric brain (not RAG chatbot), Guru Mode / Industrial Memory, AI that speaks first (prediction + intervention) |
| Business Impact | 25% | HSE-first: prevents fatalities, avoids downtime (18–22% of unplanned downtime is fragmentation-driven), audit weeks → seconds |
| Technical Excellence | 20% | Knowledge graph with continuous merge, hybrid retrieval (graph + vector), multi-agent LangGraph, real-document corpus |
| Scalability | 15% | Industry-agnostic engine, demonstrated on refinery; connector-based production architecture |
| User Experience | 15% | Role-based screens, mobile copilot for field technicians, one-click actions, live graph visuals |

**What actually wins:** Judges reward *intelligence* (predicts, reasons, recommends, acts) over *features* (searches, answers, summarizes). Evaluation focus in the PS: entity extraction accuracy, answer quality with citations, graph linkage completeness, **time-to-answer vs traditional search**, compliance gap detection — every one is a demo moment.

---

## 11. 5-Minute Demo Script

1. **Feed the brain** — Upload a messy folder (scanned P&ID, work orders Excel, incident PDFs, OEM manual, emails). Knowledge graph builds live on screen — nodes appearing and connecting.
2. **The biography** — Click Pump P-101 → Equipment 360: its whole life in one view.
3. **Ask it** (mobile) — Technician: "P-101 vibration high, what do I check?" → cited answer from manual + past work order + retired guru's voice note, credited by name.
4. **It predicts, unprompted** — Prediction card: "81% probability bearing replacement within 30 days" with clickable evidence → one-click work order draft.
5. **It intervenes** (HSE climax) — Create hot work permit on T-205 → ⚠️ intervention: 2023 near-miss INC-2023-41 + OISD-105 gas testing requirement + acknowledgment checklist.
6. **The guru lives on** — Rajesh Kumar records a Hindi voice note; show it instantly appearing in the graph and in copilot answers.
7. **One click to audit-ready** — "Generate Audit Package" → compliance PDF in seconds. Dashboard close-up.
8. **Closing metric** — "Time-to-answer: 8 seconds vs 2–3 hours. Every document you saw is a real industrial document."

---

## 12. Expected Deliverables (per PS)

- ✅ Working Prototype (the 6 flows above)
- ✅ Architecture Diagram (the 3-layer structure: Knowledge → Intelligence → Action)
- ✅ Presentation Deck (HSE-first narrative)
- ✅ Demo Video (the 8-scene script above)

---

## 13. Key Decisions Log (Why We Chose What We Chose)

| Decision | Reason |
|---|---|
| PS 8 over PS 2/4/6 | Perfect stack fit (full-stack + RAG + ML, no hardware/IoT); differentiated via equipment-centric + HSE angle to escape the "generic RAG" crowd |
| Equipment-centric graph over document RAG | Mirrors how real industrial software works; visual; memorable |
| HSE-first positioning | Maintainer's workshop hint; PS8 says "it is a safety problem" first; likely sponsor/judge priority |
| Oil & Gas demo industry | Only industry with fully public regulations, incident reports, manuals, P&IDs, and work-order datasets |
| Real documents + fictional plant | Authenticity ("every document is real") + coherence (consistent asset hierarchy) without weeks of dataset hunting |
| Prediction via interval statistics | High wow, low effort, guaranteed to work on controlled synthetic dates; honest under judge questioning |
| Simulation shows reasoning, not invented numbers | Fake precise figures collapse under one judge question |
| Cut Time Machine | High build cost, demonstrates visualization not intelligence |
| Ship 9 polished demo moments, not 15 half-built features | A working demo of fewer features beats a broken demo of many — every time |
