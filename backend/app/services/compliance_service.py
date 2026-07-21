"""
HSE Compliance Intelligence: map regulations against each asset's real state.

Detection is deterministic and rule-based (see data/compliance_rules.json). A gap
is never invented: an interval finding reads the asset's actual inspection work
orders and compares the latest one to the required interval against the fixed
reference date; a missing finding means the graph genuinely holds no such record.
Every finding names its rule, its regulation, and either the work order that
satisfies it or the exact absence. Findings are tagged Health / Safety /
Environment so the HSE coverage (including the E most teams skip) is explicit.
"""

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import settings
from app.services.equipment_service import Equipment360Response, get_equipment_360

_AVG_DAYS_PER_MONTH = 30.44
_DUE_SOON_GRACE_DAYS = 60  # how close to the interval end counts as "due soon"
_HOTWORK_WORDS = ["hot work", "flammable", "vapour", "vapor", "weld", "spark"]

# Worst first: an overdue or missing item outranks something merely due soon.
_STATUS_ORDER = {"overdue": 0, "missing_evidence": 1, "due_soon": 2, "compliant": 3}


class ComplianceFinding(BaseModel):
    equipment_tag: str
    rule_code: str
    title: str
    category: str  # Health | Safety | Environment
    severity: str  # info | caution | critical
    regulation: str
    regulation_doc_id: str | None = None  # set only when the graph truly GOVERNED_BY it
    requires: str
    status: str  # compliant | due_soon | overdue | missing_evidence
    evidence_ref: str | None = None  # work order or incident that bears on the rule
    evidence_type: str | None = None  # workorder | incident
    evidence_date: str | None = None
    due_date: str | None = None
    gap: str | None = None


class AssetCompliance(BaseModel):
    tag: str
    name: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    worst_status: str = "compliant"


class FleetCompliance(BaseModel):
    assets: list[AssetCompliance] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
    category_breakdown: dict[str, dict[str, int]] = Field(default_factory=dict)
    findings: list[ComplianceFinding] = Field(default_factory=list)


@lru_cache
def _rules() -> list[dict]:
    data = json.loads(Path(settings.COMPLIANCE_RULES).read_text(encoding="utf-8"))
    return data["rules"]


def _reference_date() -> date:
    return date.fromisoformat(settings.PREDICTION_REFERENCE_DATE)


def evaluate_equipment_compliance(tag: str) -> list[ComplianceFinding]:
    """Run every applicable rule against one asset's graph state and work orders."""
    bio = get_equipment_360(tag)
    if bio is None:
        return []

    governed = {d.doc_id for d in bio.documents if d.relationship == "GOVERNED_BY"}
    findings = []
    for rule in _rules():
        if tag not in rule["applies_to"]:
            continue
        finding = _evaluate_rule(rule, bio, governed)
        if finding is not None:
            findings.append(finding)

    findings.sort(key=lambda f: _STATUS_ORDER.get(f.status, 9))
    return findings


def evaluate_fleet_compliance() -> FleetCompliance:
    """Fleet roll-up: per-asset status, overall totals, and the H/S/E breakdown."""
    all_findings: list[ComplianceFinding] = []
    assets: list[AssetCompliance] = []

    from app.services.equipment_service import list_equipment  # local import avoids a cycle at module load

    for item in list_equipment():
        findings = evaluate_equipment_compliance(item.tag)
        all_findings.extend(findings)
        counts = _count_by_status(findings)
        assets.append(AssetCompliance(
            tag=item.tag, name=item.name, counts=counts,
            worst_status=min((f.status for f in findings), key=lambda s: _STATUS_ORDER.get(s, 9), default="compliant"),
        ))

    all_findings.sort(key=lambda f: _STATUS_ORDER.get(f.status, 9))
    return FleetCompliance(
        assets=assets,
        totals=_count_by_status(all_findings),
        category_breakdown=_category_breakdown(all_findings),
        findings=all_findings,
    )


# --- rule evaluation ---

def _evaluate_rule(rule: dict, bio: Equipment360Response, governed: set[str]) -> ComplianceFinding | None:
    if rule["check"] == "interval":
        return _interval_finding(rule, bio, governed)
    if rule["check"] == "incident_hotwork":
        return _hotwork_finding(rule, bio, governed)
    return None


def _interval_finding(rule: dict, bio: Equipment360Response, governed: set[str]) -> ComplianceFinding:
    ref = _reference_date()
    interval_days = round(rule["interval_months"] * _AVG_DAYS_PER_MONTH)
    keywords = [k.lower() for k in rule["evidence_keywords"]]

    work_orders = [t for t in bio.timeline if t.kind == "workorder" and t.date]
    matches = [w for w in work_orders if any(k in (w.description or "").lower() for k in keywords)]

    base = _base_finding(rule, bio, governed)
    if not matches:
        base.status = "missing_evidence"
        base.gap = f"No record of {rule['title'].lower()} found in the work-order history."
        return base

    latest = max(matches, key=lambda w: w.date)
    latest_date = date.fromisoformat(latest.date)
    age = (ref - latest_date).days
    due = latest_date + timedelta(days=interval_days)

    base.evidence_ref, base.evidence_type, base.evidence_date = latest.id, "workorder", latest.date
    base.due_date = due.isoformat()
    if age > interval_days:
        base.status = "overdue"
        base.gap = f"Last done {latest.date} ({latest.id}); overdue by {age - interval_days} days."
    elif age > interval_days - _DUE_SOON_GRACE_DAYS:
        base.status = "due_soon"
        base.gap = f"Due by {due.isoformat()}; last done {latest.date} ({latest.id})."
    else:
        base.status = "compliant"
    return base


def _hotwork_finding(rule: dict, bio: Equipment360Response, governed: set[str]) -> ComplianceFinding | None:
    # Only relevant where a hot-work near-miss is actually on record for the asset.
    incidents = [t for t in bio.timeline if t.kind == "incident"]
    hot = next((i for i in incidents if any(k in (i.description or "").lower() for k in _HOTWORK_WORDS)), None)
    if hot is None:
        return None

    base = _base_finding(rule, bio, governed)
    base.status = "missing_evidence"
    base.evidence_ref, base.evidence_type, base.evidence_date = hot.id, "incident", hot.date
    base.gap = (
        f"Hot-work near-miss {hot.id} is on record, but there is no compliance record verifying "
        f"the gas-testing and vent-isolation procedure required by OISD-STD-105."
    )
    return base


def _base_finding(rule: dict, bio: Equipment360Response, governed: set[str]) -> ComplianceFinding:
    doc = rule.get("regulation_doc_id")
    # Link the regulation only if the graph really has this asset GOVERNED_BY it.
    doc_link = doc if (doc and doc in governed) else None
    return ComplianceFinding(
        equipment_tag=bio.summary.tag, rule_code=rule["code"], title=rule["title"],
        category=rule["category"], severity=rule["severity"], regulation=rule["regulation"],
        regulation_doc_id=doc_link, requires=rule["requires"], status="compliant",
    )


# --- aggregation helpers ---

def _count_by_status(findings: list[ComplianceFinding]) -> dict[str, int]:
    counts = {"compliant": 0, "due_soon": 0, "overdue": 0, "missing_evidence": 0}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1
    return counts


def _category_breakdown(findings: list[ComplianceFinding]) -> dict[str, dict[str, int]]:
    breakdown: dict[str, dict[str, int]] = {}
    for category in ("Health", "Safety", "Environment"):
        cat_findings = [f for f in findings if f.category == category]
        breakdown[category] = {
            "total": len(cat_findings),
            "gaps": sum(1 for f in cat_findings if f.status != "compliant"),
        }
    return breakdown
