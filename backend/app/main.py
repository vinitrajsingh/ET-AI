"""
FastAPI entry point for SANJEEVANI.

Wires up CORS (so the Next.js frontend at localhost:3000 can call the API),
ensures the Qdrant collection exists on startup, and mounts the health router.
Feature routers (ingestion, copilot, equipment) are stubs for now and will be
included here as they are built.

Run:  uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.neo4j_client import close_driver
from app.db.qdrant_client import ensure_collection
from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: make sure the vector collection exists. Best-effort — if Qdrant
    # isn't up yet, don't crash the whole app; /health will report it as down.
    try:
        ensure_collection()
    except Exception as exc:
        print(f"[startup] Qdrant collection not ready: {exc}")
    yield
    # Shutdown: release the Neo4j connection pool.
    close_driver()


app = FastAPI(title="SANJEEVANI API", version="0.1.0", lifespan=lifespan)

# Allow the Next.js dev server to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)

# Feature routers — uncomment as each is implemented:
# from app.routers import ingestion, copilot, equipment
# app.include_router(ingestion.router)
# app.include_router(copilot.router)
# app.include_router(equipment.router)
