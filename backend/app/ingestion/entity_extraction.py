"""
Stage 2: text -> structured entities. The hardest, most error-prone stage, so it
lives on its own and is deliberately explicit.

Two paths:
  - Structured tables (the work-order Excel) are parsed directly into entities.
    Tables are trustworthy; running them through an LLM would only add mistakes.
  - Free text (manuals, regulations, incidents, emails, P&ID descriptions) goes
    through one OpenAI call constrained to a strict JSON schema, validated with
    pydantic. Malformed output is retried once, then skipped with a warning so a
    single bad document never crashes a bulk ingest.
"""

import logging
import re

from pydantic import BaseModel, Field, ValidationError

from app.services.llm import complete_json

logger = logging.getLogger(__name__)

_INCIDENT_REF_RE = re.compile(r"INC-\d{4}-\d+")
# Non-humans that show up in the work-order "technician"/"reported_by" columns.
_NOT_A_PERSON = {"unassigned", "auto-pm scheduler"}


# --- Entity models (also the JSON contract the LLM must follow) ---

class EquipmentEntity(BaseModel):
    tag: str
    name: str | None = None
    type: str | None = None
    location: str | None = None


class PersonEntity(BaseModel):
    name: str
    role: str | None = None


class IncidentEntity(BaseModel):
    id: str | None = None
    date: str | None = None
    title: str | None = None
    description: str | None = None
    equipment_tag: str | None = None


class WorkOrderEntity(BaseModel):
    wo_id: str
    equipment_tag: str
    date: str | None = None
    wo_type: str | None = None
    description: str | None = None
    parts_used: str | None = None
    cost: float | None = None
    technician: str | None = None
    status: str | None = None


class RegulationEntity(BaseModel):
    code: str
    title: str | None = None
    clause: str | None = None
    description: str | None = None
    equipment_tag: str | None = None


class FailureModeEntity(BaseModel):
    name: str
    description: str | None = None
    equipment_tag: str | None = None


class ExtractedEntities(BaseModel):
    equipment: list[EquipmentEntity] = Field(default_factory=list)
    people: list[PersonEntity] = Field(default_factory=list)
    incidents: list[IncidentEntity] = Field(default_factory=list)
    work_orders: list[WorkOrderEntity] = Field(default_factory=list)
    regulations: list[RegulationEntity] = Field(default_factory=list)
    failure_modes: list[FailureModeEntity] = Field(default_factory=list)


# --- Path A: structured tables ---

def work_orders_from_table(rows: list[dict]) -> ExtractedEntities:
    """
    Turn work-order rows straight into entities. Also derives the equipment and
    people they touch, and pulls any 'INC-YYYY-NN' reference out of the notes so
    the near-miss on T-205 links back to its incident.
    """
    result = ExtractedEntities()
    seen_equipment: set[str] = set()
    seen_people: set[str] = set()
    seen_incidents: set[str] = set()

    for row in rows:
        tag = _clean(row.get("equipment_tag"))
        wo_id = _clean(row.get("wo_id"))
        if not tag or not wo_id:
            continue

        wo_date = _clean(row.get("completed_date")) or _clean(row.get("reported_date"))
        result.work_orders.append(
            WorkOrderEntity(
                wo_id=wo_id,
                equipment_tag=tag,
                date=wo_date,
                wo_type=_clean(row.get("wo_type")),
                description=_clean(row.get("description")),
                parts_used=_clean(row.get("parts_used")),
                cost=_to_float(row.get("cost_inr")),
                technician=_clean(row.get("technician")),
                status=_clean(row.get("status")),
            )
        )

        if tag not in seen_equipment:
            seen_equipment.add(tag)
            result.equipment.append(EquipmentEntity(tag=tag, name=_clean(row.get("equipment_name"))))

        # Only the technician gets a Person node here, so every person we create
        # is tied to equipment through a work order (no dangling people).
        person = _clean(row.get("technician"))
        if person and person.lower() not in _NOT_A_PERSON and person not in seen_people:
            seen_people.add(person)
            result.people.append(PersonEntity(name=person))

        # A work order that references an incident id carries the near-miss story
        # and its date, so the incident inherits that date for the timeline.
        for inc_id in _INCIDENT_REF_RE.findall(row.get("description") or ""):
            if inc_id not in seen_incidents:
                seen_incidents.add(inc_id)
                result.incidents.append(
                    IncidentEntity(
                        id=inc_id, date=wo_date, equipment_tag=tag,
                        description=_clean(row.get("description")),
                    )
                )

    return result


# --- Path B: free text via the LLM ---

_SYSTEM = (
    "You extract structured data from oil-refinery documents. "
    "Return ONLY facts present in the text. Do not invent equipment tags, names, "
    "dates, or clause numbers. Equipment tags look like P-101, C-201, T-205, "
    "HX-301, B-7. If a field is unknown, omit it."
)

_SCHEMA_HINT = """Return a JSON object with these keys (use empty arrays when nothing applies):
{
  "equipment":     [{"tag": "P-101", "name": "", "type": "", "location": ""}],
  "people":        [{"name": "", "role": ""}],
  "incidents":     [{"id": "", "date": "", "title": "", "description": "", "equipment_tag": ""}],
  "regulations":   [{"code": "OISD-STD-105", "title": "", "clause": "", "description": "", "equipment_tag": ""}],
  "failure_modes": [{"name": "bearing failure", "description": "", "equipment_tag": ""}]
}
Only include an equipment_tag on an item if that tag actually appears in the text."""


def extract_entities(text: str, known_tags: list[str] | None = None, max_chars: int = 12000) -> ExtractedEntities:
    """
    Extract entities from free text with one validated LLM call.

    We cap the input length because entity density is highest near the top of a
    document and full manuals would be wasteful to send. `known_tags` (e.g. tags
    the extractor already saw in a filename) are passed as a hint to improve
    linking, not as permission to invent.
    """
    if not text.strip():
        return ExtractedEntities()

    hint = f"\nEquipment tags already known for this document: {known_tags}" if known_tags else ""
    user = f"{_SCHEMA_HINT}{hint}\n\nDOCUMENT:\n{text[:max_chars]}"

    raw = _call_with_retry(user)
    if raw is None:
        return ExtractedEntities()
    try:
        return ExtractedEntities.model_validate(raw)
    except ValidationError as exc:
        logger.warning("Entity JSON failed validation, skipping: %s", exc)
        return ExtractedEntities()


def _call_with_retry(user: str) -> dict | None:
    """One LLM call, retried once on a transport/parse error, then give up."""
    for attempt in (1, 2):
        try:
            return complete_json(_SYSTEM, user)
        except Exception as exc:
            logger.warning("Entity extraction attempt %d failed: %s", attempt, exc)
    return None


# --- small helpers ---

def _clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_float(value) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
