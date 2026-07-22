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
from app.db.schema import setup_constraints
from app.routers import (
    audit,
    compliance,
    copilot,
    equipment,
    guru,
    health,
    ingestion,
    permits,
    prediction,
    workorders,
)
from app.services.permit_service import init_permit_storage
from app.services.workorder_draft_service import init_workorder_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: make sure the vector collection and graph constraints exist. Both
    # are best-effort. If a DB isn't up yet, don't crash the whole app; /health
    # will report it as down.
    try:
        ensure_collection()
    except Exception as exc:
        print(f"[startup] Qdrant collection not ready: {exc}")
    try:
        setup_constraints()
    except Exception as exc:
        print(f"[startup] Neo4j constraints not applied: {exc}")
    try:
        init_permit_storage()
        init_workorder_storage()
    except Exception as exc:
        print(f"[startup] Postgres tables not ready: {exc}")
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
app.include_router(ingestion.router)
app.include_router(equipment.router)
app.include_router(prediction.router)
app.include_router(copilot.router)
app.include_router(permits.router)
app.include_router(guru.router)
app.include_router(compliance.router)
app.include_router(audit.router)
app.include_router(workorders.router)
