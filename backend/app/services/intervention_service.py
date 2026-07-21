"""
The AI Intervention Engine: proactive safety checks before a permit is activated.

The whole point of this phase is that detection is DETERMINISTIC graph logic, not
an LLM guess. The system does not think hot work on T-205 "seems risky"; it knows,
because the graph records the 2023 near-miss (INC-2023-41) and the OISD-105 edge
that governs the tank. Three explainable rules run against facts we already store:

  1. Past incidents  - the asset has a HAS_INCIDENT, worst when it matches the
     permit's hazard (hot-work permit + hot-work near-miss = critical).
  2. Governing rules  - the permit type maps to a regulation concern, and we only
     cite it after confirming the asset is actually GOVERNED_BY that regulation.
  3. Conflicts        - another active permit or an open corrective work order on
     the same asset means simultaneous operations.

Every item cites a real graph fact and links into Equipment 360. If nothing
applies, the permit proceeds with an empty result, which is an honest answer.
"""

from pydantic import BaseModel, Field

from app.services.equipment_service import Equipment360Response, get_equipment_360
from app.services.permit_service import active_permits_for

# Permit types offered in the UI. Kept here so the frontend and rules agree.
PERMIT_TYPES = ["Hot Work", "Confined Space Entry", "Working at Height", "General Maintenance"]

# Words that mean an incident shares a permit's hazard context. Transparent on
# purpose so the "why is this critical?" answer is a keyword match, not a vibe.
_INCIDENT_KEYWORDS: dict[str, list[str]] = {
    "Hot Work": ["hot work", "welding", "flame", "spark", "flammable", "vapour", "vapor", "ignition"],
    "Confined Space Entry": ["confined space", "entry", "oxygen", "vessel", "purge"],
    "Working at Height": ["height", "fall", "scaffold", "ladder"],
    "General Maintenance": [],
}

# permit type -> the regulation that governs it and the precaution it demands.
# We still confirm the asset is GOVERNED_BY the code before citing it.
_REGULATION_RULES: dict[str, dict] = {
    "Hot Work": {
        "codes": ["OISD-STD-105"],
        "risk": "critical",
        "concern": (
            "OISD-STD-105 requires a hot work permit with gas testing before and during the job. "
            "Confirm the atmosphere is tested and below the lower explosive limit, and that all "
            "vents and connected lines are positively isolated before any spark or flame."
        ),
    },
    "Confined Space Entry": {
        "codes": ["OISD-STD-105"],
        "risk": "critical",
        "concern": (
            "OISD-STD-105 requires a confined space entry permit with continuous gas monitoring "
            "and a trained standby person stationed at the entry point."
        ),
    },
    "Working at Height": {
        "codes": [],
        "risk": "caution",
        "concern": "Ensure fall-protection harnesses and scaffold inspection are in place.",
    },
    "General Maintenance": {"codes": [], "risk": "info", "concern": ""},
}

_SEVERITY_ORDER = {"critical": 0, "caution": 1, "info": 2}


class Citation(BaseModel):
    type: str  # incident | document | workorder | permit
    ref: str
    equipment_tag: str | None = None
    title: str | None = None


class InterventionItem(BaseModel):
    id: str  # stable key, e.g. "incident:INC-2023-41", used for acknowledgment
    severity: str  # info | caution | critical
    title: str
    body: str
    citation: Citation | None = None
    requires_acknowledgment: bool = False


class InterventionResult(BaseModel):
    equipment_tag: str
    permit_type: str
    items: list[InterventionItem] = Field(default_factory=list)
    has_blocking: bool = False  # a critical item still needs acknowledging


def evaluate_permit(permit_type: str, equipment_tag: str, description: str = "") -> InterventionResult:
    """Run the three rules against the asset's graph facts. No LLM, no invention."""
    bio = get_equipment_360(equipment_tag)
    if bio is None:
        # Unknown asset: nothing to check. Honest empty result rather than an error.
        return InterventionResult(equipment_tag=equipment_tag, permit_type=permit_type)

    items = _incident_items(permit_type, bio) + _regulation_items(permit_type, bio) + _conflict_items(bio)
    items.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 9))

    has_blocking = any(i.severity == "critical" and i.requires_acknowledgment for i in items)
    return InterventionResult(
        equipment_tag=equipment_tag, permit_type=permit_type, items=items, has_blocking=has_blocking
    )


def _incident_items(permit_type: str, bio: Equipment360Response) -> list[InterventionItem]:
    """Recall past incidents, escalating when the incident shares the permit hazard."""
    keywords = _INCIDENT_KEYWORDS.get(permit_type, [])
    items = []
    for event in bio.timeline:
        if event.kind != "incident":
            continue
        matches_hazard = any(k in (event.description or "").lower() for k in keywords)
        severity = "critical" if matches_hazard else "caution"
        prefix = "Directly relevant near-miss" if matches_hazard else "Past incident on this asset"
        items.append(InterventionItem(
            id=f"incident:{event.id}",
            severity=severity,
            title=f"{prefix}: {event.id}",
            body=event.description or "A safety incident is on record for this equipment.",
            citation=Citation(type="incident", ref=event.id, equipment_tag=bio.summary.tag, title=event.id),
            requires_acknowledgment=(severity == "critical"),
        ))
    return items


def _regulation_items(permit_type: str, bio: Equipment360Response) -> list[InterventionItem]:
    """Cite a governing regulation, but only if the asset is really GOVERNED_BY it."""
    rule = _REGULATION_RULES.get(permit_type)
    if not rule or not rule["codes"]:
        return []

    governed = {d.doc_id for d in bio.documents if d.relationship == "GOVERNED_BY"}
    items = []
    for code in rule["codes"]:
        if code not in governed:
            continue  # do not cite a rule the graph does not actually link to this asset
        items.append(InterventionItem(
            id=f"document:{code}",
            severity=rule["risk"],
            title=f"{code} applies to {permit_type.lower()} on {bio.summary.tag}",
            body=rule["concern"],
            citation=Citation(type="document", ref=code, equipment_tag=bio.summary.tag, title=code),
            requires_acknowledgment=(rule["risk"] in ("critical", "caution")),
        ))
    return items


def _conflict_items(bio: Equipment360Response) -> list[InterventionItem]:
    """Flag simultaneous operations: open corrective work orders or active permits."""
    items = []

    for event in bio.timeline:
        # Only an open corrective job is a simultaneous-operations concern; routine
        # open inspections are not, so a benign permit stays clean.
        is_open_corrective = (
            event.kind == "workorder"
            and event.status
            and event.status != "Closed"
            and event.extra.get("wo_type") == "Corrective"
        )
        if is_open_corrective:
            items.append(InterventionItem(
                id=f"workorder:{event.id}",
                severity="caution",
                title=f"Open corrective work order {event.id} in progress",
                body=(
                    f"{event.id} ({event.status}) is active on this equipment: "
                    f"{event.description}. Coordinate to avoid simultaneous operations."
                ),
                citation=Citation(type="workorder", ref=event.id, equipment_tag=bio.summary.tag, title=event.id),
                requires_acknowledgment=False,
            ))

    for permit in active_permits_for(bio.summary.tag):
        items.append(InterventionItem(
            id=f"permit:{permit.permit_id}",
            severity="caution",
            title=f"Active permit {permit.permit_id} already on this asset",
            body=f"A {permit.permit_type} permit ({permit.permit_id}) is already active here. Confirm the work is compatible.",
            citation=Citation(type="permit", ref=permit.permit_id, equipment_tag=bio.summary.tag, title=permit.permit_id),
            requires_acknowledgment=False,
        ))

    return items
