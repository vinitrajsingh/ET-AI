"""
Ingestion endpoints.

  POST /ingest       upload one file, run the pipeline, return its summary
  POST /ingest/bulk  ingest the whole demo corpus folder (seed the demo)

The upload is saved to a temp file because the extractors work on file paths
(PyMuPDF, pandas, etc. all expect a path, not a stream).
"""

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.ingestion.pipeline import DirectorySummary, IngestSummary, ingest_directory, ingest_file

router = APIRouter(tags=["ingestion"])


@router.post("/ingest", response_model=IngestSummary)
async def ingest(file: UploadFile = File(...)) -> IngestSummary:
    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    # Keep the original name so doc_id/title come from it, not the temp name.
    target = tmp_path.with_name(file.filename or tmp_path.name)
    tmp_path.rename(target)
    try:
        return ingest_file(target)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc))
    finally:
        target.unlink(missing_ok=True)


@router.post("/ingest/bulk", response_model=DirectorySummary)
def ingest_bulk() -> DirectorySummary:
    root = Path(settings.DATA_DIR)
    if not root.exists():
        raise HTTPException(status_code=404, detail=f"Corpus folder not found: {root}")
    return ingest_directory(root)
