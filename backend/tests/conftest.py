"""Shared test helpers: locate real corpus samples to exercise the pipeline."""

from pathlib import Path

import pytest

from app.config import settings

CORPUS = Path(settings.DATA_DIR)


def _first(pattern: str) -> Path | None:
    matches = sorted(CORPUS.rglob(pattern))
    return matches[0] if matches else None


@pytest.fixture(scope="session")
def workorders_xlsx() -> Path:
    path = _first("*WorkOrders*.xlsx") or _first("*.xlsx")
    if path is None:
        pytest.skip("No work-order spreadsheet in corpus")
    return path


@pytest.fixture(scope="session")
def sample_pdf() -> Path:
    path = _first("*.pdf")
    if path is None:
        pytest.skip("No PDF in corpus")
    return path


@pytest.fixture(scope="session")
def sample_pid() -> Path:
    path = _first("PID_*.png") or _first("*.png")
    if path is None:
        pytest.skip("No P&ID image in corpus")
    return path
