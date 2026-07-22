"""
Audit package assembly: gather everything the system knows into one structured
report an HSE manager could hand to an auditor.

Pure composition, no new intelligence and nothing invented. Every section is
pulled from an existing service: compliance findings, incidents, permit
acknowledgment logs (the Phase 6 audit trail, which is the centerpiece), the work
orders that satisfy rules, and current predictions with their evidence. We build a
structured model first so the JSON preview and the PDF render from the same source.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.config import settings
from app.services.compliance_service import ComplianceFinding, evaluate_equipment_compliance
from app.services.equipment_service import get_equipment_360, list_equipment
from app.services.permit_service import list_permits
from app.services.prediction_service import get_predictions

_PLANT_NAME = "Bharat Petrochem Unit-2"


class AuditCover(BaseModel):
    plant_name: str
    scope: str
    generated_at: str
    reference_date: str


class EquipmentRow(BaseModel):
    tag: str
    name: str | None = None
    type: str | None = None
    location: str | None = None
    work_orders: int = 0
    incidents: int = 0


class IncidentRow(BaseModel):
    id: str
    equipment_tag: str
    date: str | None = None
    description: str | None = None


class AcknowledgedItem(BaseModel):
    title: str
    severity: str
    cited: str | None = None  # the incident/regulation the intervention cited


class PermitRow(BaseModel):
    permit_id: str
    permit_type: str
    equipment_tag: str
    created_by: str | None = None
    created_date: str
    acknowledged: list[AcknowledgedItem] = Field(default_factory=list)


class MaintenanceRow(BaseModel):
    wo_id: str
    equipment_tag: str
    date: str | None = None
    status: str | None = None
    description: str | None = None
    note: str  # why it is in the pack (satisfies a rule / open / overdue)


class PredictionRow(BaseModel):
    equipment_tag: str
    failure_label: str
    risk_level: str | None = None
    confidence: int | None = None
    predicted_center: str | None = None
    evidence: list[str] = Field(default_factory=list)


class AuditPackage(BaseModel):
    cover: AuditCover
    equipment: list[EquipmentRow] = Field(default_factory=list)
    compliance: list[ComplianceFinding] = Field(default_factory=list)
    incidents: list[IncidentRow] = Field(default_factory=list)
    permits: list[PermitRow] = Field(default_factory=list)
    maintenance: list[MaintenanceRow] = Field(default_factory=list)
    predictions: list[PredictionRow] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


def build_audit_package(scope: str = "fleet") -> AuditPackage:
    """Assemble the package for the whole fleet or a single equipment tag."""
    tags = _resolve_scope(scope)

    # Fetch each asset's 360 once and reuse it across every section. Against a
    # cloud graph these calls dominate the time, so caching them here is what keeps
    # generation to a few seconds instead of tens.
    bios = {tag: get_equipment_360(tag) for tag in tags}

    compliance = [f for tag in tags for f in evaluate_equipment_compliance(tag, bios[tag])]
    equipment = _equipment_rows(tags, bios)
    incidents = _incident_rows(tags, bios)
    permits = _permit_rows(tags)
    maintenance = _maintenance_rows(tags, bios, compliance)
    predictions = _prediction_rows(tags)

    return AuditPackage(
        cover=AuditCover(
            plant_name=_PLANT_NAME,
            scope="Full fleet" if scope == "fleet" else scope,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            reference_date=settings.PREDICTION_REFERENCE_DATE,
        ),
        equipment=equipment,
        compliance=compliance,
        incidents=incidents,
        permits=permits,
        maintenance=maintenance,
        predictions=predictions,
        summary=_summary(compliance, permits, maintenance),
    )


def _resolve_scope(scope: str) -> list[str]:
    all_tags = [e.tag for e in list_equipment()]
    if scope == "fleet":
        return all_tags
    return [scope] if scope in all_tags else []


def _equipment_rows(tags: list[str], bios: dict) -> list[EquipmentRow]:
    rows = []
    for item in list_equipment():
        if item.tag in tags:
            summary = bios[item.tag].summary if bios.get(item.tag) else None
            rows.append(EquipmentRow(
                tag=item.tag, name=item.name,
                type=summary.type if summary else None,
                location=summary.location if summary else None,
                work_orders=item.work_orders, incidents=item.incidents,
            ))
    return rows


def _incident_rows(tags: list[str], bios: dict) -> list[IncidentRow]:
    rows: list[IncidentRow] = []
    seen: set[str] = set()
    for tag in tags:
        bio = bios.get(tag)
        if not bio:
            continue
        for event in bio.timeline:
            if event.kind == "incident" and event.id not in seen:
                seen.add(event.id)
                rows.append(IncidentRow(id=event.id, equipment_tag=tag, date=event.date, description=event.description))
    return rows


def _permit_rows(tags: list[str]) -> list[PermitRow]:
    rows = []
    for permit in list_permits():
        if permit.equipment_tag not in tags:
            continue
        acknowledged = [
            AcknowledgedItem(
                title=item.get("title", ""),
                severity=item.get("severity", ""),
                cited=(item.get("citation") or {}).get("ref"),
            )
            for item in permit.acknowledged_items
        ]
        rows.append(PermitRow(
            permit_id=permit.permit_id, permit_type=permit.permit_type, equipment_tag=permit.equipment_tag,
            created_by=permit.created_by, created_date=permit.created_date.strftime("%Y-%m-%d %H:%M"),
            acknowledged=acknowledged,
        ))
    return rows


def _maintenance_rows(tags: list[str], bios: dict, compliance: list[ComplianceFinding]) -> list[MaintenanceRow]:
    """Work orders that satisfy a rule, plus any open work orders on the assets."""
    rows: list[MaintenanceRow] = []
    seen: set[str] = set()

    for finding in compliance:
        if finding.evidence_type == "workorder" and finding.evidence_ref and finding.evidence_ref not in seen:
            seen.add(finding.evidence_ref)
            note = "Overdue" if finding.status == "overdue" else f"Satisfies {finding.rule_code}"
            rows.append(MaintenanceRow(
                wo_id=finding.evidence_ref, equipment_tag=finding.equipment_tag,
                date=finding.evidence_date, status="Closed", description=finding.title, note=note,
            ))

    for tag in tags:
        bio = bios.get(tag)
        if not bio:
            continue
        for event in bio.timeline:
            if event.kind == "workorder" and event.status and event.status != "Closed" and event.id not in seen:
                seen.add(event.id)
                rows.append(MaintenanceRow(
                    wo_id=event.id, equipment_tag=tag, date=event.date, status=event.status,
                    description=event.description, note="Open work order",
                ))
    return rows


def _prediction_rows(tags: list[str]) -> list[PredictionRow]:
    rows = []
    for tag in tags:
        for p in get_predictions(tag):
            if p.status == "predicted":
                rows.append(PredictionRow(
                    equipment_tag=tag, failure_label=p.failure_label, risk_level=p.risk_level,
                    confidence=p.confidence, predicted_center=p.predicted_center,
                    evidence=[e.wo_id for e in p.evidence],
                ))
    return rows


def _summary(compliance, permits, maintenance) -> dict:
    counts = {"compliant": 0, "due_soon": 0, "overdue": 0, "missing_evidence": 0}
    for f in compliance:
        counts[f.status] = counts.get(f.status, 0) + 1
    return {
        **counts,
        "permits": len(permits),
        "acknowledged_interventions": sum(len(p.acknowledged) for p in permits),
        "open_or_overdue_maintenance": sum(1 for m in maintenance if m.note in ("Open work order", "Overdue")),
    }
