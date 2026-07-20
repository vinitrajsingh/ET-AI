"""Stage 1: every extractor pulls real text/structure out of a real corpus file."""

from app.ingestion.extractors import excel, pdf, pid
from app.ingestion.text_extraction import extract_text


def test_pdf_extractor_returns_text(sample_pdf):
    content = pdf.extract(sample_pdf)
    assert content.text.strip(), "PDF extractor returned empty text"


def test_excel_extractor_returns_rows(workorders_xlsx):
    content = excel.extract(workorders_xlsx)
    assert content.doc_type == "workorders"
    assert content.tables and content.tables[0], "Excel extractor returned no rows"


def test_pid_extractor_reads_tag_from_filename(sample_pid):
    # Vision is off here so the test stays offline and free; the filename alone
    # must still yield the equipment tag.
    content = pid.extract(sample_pid, use_vision=False)
    assert content.equipment_tags, "P&ID extractor found no equipment tag in filename"


def test_router_dispatches_by_extension(workorders_xlsx):
    content = extract_text(workorders_xlsx)
    assert content.doc_type == "workorders"
