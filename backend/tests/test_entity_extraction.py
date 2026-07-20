"""Stage 2: the work-order table yields the expected entities, no LLM involved."""

from app.ingestion.extractors import excel
from app.ingestion.entity_extraction import work_orders_from_table


def test_workorder_rows_yield_p101(workorders_xlsx):
    rows = [row for table in excel.extract(workorders_xlsx).tables for row in table]
    entities = work_orders_from_table(rows)

    tags = {e.tag for e in entities.equipment}
    assert "P-101" in tags, "Expected P-101 from the work-order sheet"
    assert entities.work_orders, "No work orders parsed"


def test_near_miss_incident_is_linked_to_t205(workorders_xlsx):
    # WO-1039 references INC-2023-41 on T-205; that link is the HSE demo moment.
    rows = [row for table in excel.extract(workorders_xlsx).tables for row in table]
    entities = work_orders_from_table(rows)

    inc = next((i for i in entities.incidents if i.id == "INC-2023-41"), None)
    assert inc is not None, "INC-2023-41 not extracted from work-order notes"
    assert inc.equipment_tag == "T-205"
