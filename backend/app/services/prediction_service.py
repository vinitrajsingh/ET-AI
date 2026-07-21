"""
Predictive maintenance by transparent interval statistics. No ML, no LLM.

The whole design goal is defensibility: every prediction points at the exact
dated work orders it came from and the arithmetic that produced it. A judge can
ask "where does this number come from?" and the answer is "these three work
orders, this mean interval". When the history is too thin to say anything honest,
we say so instead of inventing a number.

Pipeline for one asset:
  work orders -> detect recurring failures of a kind -> intervals between them
  -> mean/spread -> compare current cycle age to the mean -> risk + window.
"""

from datetime import date, timedelta
from statistics import pstdev

from pydantic import BaseModel, Field

from app.config import settings
from app.db.neo4j_client import get_driver

_AVG_DAYS_PER_MONTH = 30.44


class FailureSignature(BaseModel):
    """How to recognise one kind of recurring failure in free-text descriptions."""

    label: str
    components: list[str]  # the part involved, e.g. "bearing"
    actions: list[str]  # words that indicate it failed or was replaced


# A work order counts as this failure kind when it names the component AND an
# action, and does not explicitly say the work was NOT done ("no bearing work").
# Only "bearing" ships now; seal / tube-leak / valve can be added here later with
# no code change, once their keywords are tuned against the corpus.
FAILURE_SIGNATURES: dict[str, FailureSignature] = {
    "bearing": FailureSignature(
        label="Bearing failure",
        components=["bearing"],
        actions=["replace", "replaced", "replacement", "failure", "failed"],
    ),
}

# Risk comes straight from how far through the average interval we are: age / mean.
# Bands are explicit on purpose so the label is auditable, not buried in a formula.
RISK_BANDS: list[tuple[float, str]] = [
    (1.0, "High"),      # at or past the average interval: overdue
    (0.8, "Elevated"),  # into the last fifth of the cycle: due soon
    (0.5, "Watch"),     # past the halfway mark
    (0.0, "Low"),
]
_RISK_ORDER = {"High": 4, "Elevated": 3, "Watch": 2, "Low": 1}

# Deterioration language that corroborates a prediction, surfaced verbatim. We
# match the trend, not the mere mention of "vibration", so steady baseline PM
# readings don't get flagged as warnings. "climb" catches climbed/climbing.
_SIGNAL_KEYWORDS = ["whistling", "climb", "rising", "trend", "creeping"]


# --- Response models ---

class EvidenceItem(BaseModel):
    wo_id: str
    date: str | None = None
    description: str | None = None


class PredictionResult(BaseModel):
    equipment_tag: str
    failure_type: str
    failure_label: str
    status: str  # "predicted" | "insufficient_history"
    cycles: int  # number of past failures detected
    reference_date: str

    # Populated when status == "predicted":
    intervals_days: list[int] = Field(default_factory=list)
    mean_interval_days: float | None = None
    mean_interval_months: float | None = None
    interval_min_days: int | None = None
    interval_max_days: int | None = None
    interval_stdev_days: float | None = None
    last_failure_date: str | None = None
    current_age_days: int | None = None
    current_age_months: float | None = None
    predicted_window_start: str | None = None
    predicted_center: str | None = None
    predicted_window_end: str | None = None
    days_until_window_start: int | None = None
    days_until_center: int | None = None
    risk_level: str | None = None
    risk_ratio: float | None = None

    confidence: int | None = None  # 0-100, from sample size + interval consistency
    confidence_note: str
    explanation: str = ""  # the plain-language "why", built for judges to read aloud
    message: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    supporting_signals: list[str] = Field(default_factory=list)


class FleetPredictionItem(BaseModel):
    tag: str
    name: str | None = None
    status: str  # "predicted" | "no_prediction"
    risk_level: str | None = None
    failure_label: str | None = None
    days_until_center: int | None = None
    message: str


# --- Detection ---

def _matches(description: str, sig: FailureSignature) -> bool:
    """True when the description names the component and an action, and isn't negated."""
    d = (description or "").lower()
    if not any(c in d for c in sig.components):
        return False
    # Skip lines that explicitly say the component was left alone, e.g.
    # "Replaced seal, no bearing work required" must not count as a bearing job.
    if any(f"no {c}" in d for c in sig.components):
        return False
    return any(a in d for a in sig.actions)


def _detect_failures(work_orders: list[dict], sig: FailureSignature) -> list[dict]:
    """Closed work orders matching the signature, oldest first. Open ones are the
    current cycle, not a past failure, so they are excluded here."""
    hits = [
        w for w in work_orders
        if w.get("status") == "Closed" and w.get("date") and _matches(w.get("description", ""), sig)
    ]
    return sorted(hits, key=lambda w: w["date"])


def _supporting_signals(work_orders: list[dict], evidence_ids: set[str]) -> list[str]:
    """Symptom notes from other work orders (rising vibration, whistling), verbatim."""
    signals = []
    for w in sorted(work_orders, key=lambda x: x.get("date") or ""):
        if w["wo_id"] in evidence_ids:
            continue
        desc = w.get("description") or ""
        if any(k in desc.lower() for k in _SIGNAL_KEYWORDS):
            signals.append(f"{w['wo_id']} ({w.get('date')}): {desc}")
    return signals


# --- Prediction ---

def _reference_date() -> date:
    return date.fromisoformat(settings.PREDICTION_REFERENCE_DATE)


def _risk_level(ratio: float) -> str:
    for threshold, label in RISK_BANDS:
        if ratio >= threshold:
            return label
    return "Low"


def _months(days: float) -> float:
    return round(days / _AVG_DAYS_PER_MONTH, 1)


def _confidence(intervals: list[int], mean: float) -> int:
    """
    A 0-100 confidence score with no ML behind it, just two honest factors:
    how many intervals we have (more history is more trustworthy) and how
    consistent they are (a tight, repeatable cycle is more trustworthy than a
    scattered one). Both are easy to explain to a judge.
    """
    spread = pstdev(intervals) if len(intervals) > 1 else 0.0
    cv = spread / mean if mean else 0.0  # relative spread, so it's scale-free
    sample_score = min(1.0, len(intervals) / 3.0)  # 1 interval -> 0.33, 3+ -> 1.0
    consistency_score = max(0.0, 1.0 - cv)  # perfectly regular intervals -> 1.0
    return round(100 * (0.5 * sample_score + 0.5 * consistency_score))


def _days_phrase(intervals: list[int]) -> str:
    """Render intervals as '550 and 513 days' / '550, 513, and 600 days'."""
    if len(intervals) == 1:
        return f"{intervals[0]} days"
    if len(intervals) == 2:
        return f"{intervals[0]} and {intervals[1]} days"
    return ", ".join(str(i) for i in intervals[:-1]) + f", and {intervals[-1]} days"


def _predict_for_signature(tag: str, work_orders: list[dict], ftype: str, sig: FailureSignature) -> PredictionResult | None:
    """Run the interval statistics for one failure kind. None if it never occurs."""
    failures = _detect_failures(work_orders, sig)
    if not failures:
        return None  # this asset has never had this failure; nothing to report

    ref = _reference_date()
    evidence = [EvidenceItem(wo_id=f["wo_id"], date=f["date"], description=f["description"]) for f in failures]

    # One failure is not a pattern: be honest rather than guess from a single point.
    if len(failures) < 2:
        return PredictionResult(
            equipment_tag=tag, failure_type=ftype, failure_label=sig.label,
            status="insufficient_history", cycles=len(failures), reference_date=ref.isoformat(),
            confidence_note=f"Based on {len(failures)} recorded {sig.label.lower()}; need at least 2 to estimate an interval.",
            message=f"Only one past {sig.label.lower()} on record. Not enough history to predict the next one.",
            evidence=evidence,
        )

    dates = [date.fromisoformat(f["date"]) for f in failures]
    intervals = [(b - a).days for a, b in zip(dates, dates[1:])]
    mean_interval = sum(intervals) / len(intervals)

    last_failure = dates[-1]
    age_days = (ref - last_failure).days
    ratio = age_days / mean_interval
    risk = _risk_level(ratio)
    stdev = round(pstdev(intervals), 1) if len(intervals) > 1 else 0.0

    window_start = last_failure + timedelta(days=min(intervals))
    center = last_failure + timedelta(days=round(mean_interval))
    window_end = last_failure + timedelta(days=max(intervals))
    days_until_center = round(mean_interval) - age_days

    confidence = _confidence(intervals, mean_interval)
    explanation = (
        f"{sig.label}s on {tag} recurred after {_days_phrase(intervals)} "
        f"(average {round(mean_interval, 1)} days, about {_months(mean_interval)} months). "
        f"The current cycle has run {age_days} days, {round(ratio * 100)}% of the average interval, "
        f"so SANJEEVANI classifies this as {risk} risk. The next {sig.label.lower()} is projected "
        f"around {center.isoformat()}, within about {days_until_center} days. "
        f"Confidence is {confidence}%, based on {len(failures)} cycles with an interval spread of {stdev} days."
    )

    return PredictionResult(
        equipment_tag=tag, failure_type=ftype, failure_label=sig.label,
        status="predicted", cycles=len(failures), reference_date=ref.isoformat(),
        intervals_days=intervals,
        mean_interval_days=round(mean_interval, 1), mean_interval_months=_months(mean_interval),
        interval_min_days=min(intervals), interval_max_days=max(intervals),
        interval_stdev_days=stdev,
        last_failure_date=last_failure.isoformat(),
        current_age_days=age_days, current_age_months=_months(age_days),
        predicted_window_start=window_start.isoformat(),
        predicted_center=center.isoformat(),
        predicted_window_end=window_end.isoformat(),
        days_until_window_start=min(intervals) - age_days,
        days_until_center=days_until_center,
        risk_level=risk, risk_ratio=round(ratio, 2),
        confidence=confidence,
        confidence_note=f"Based on {len(failures)} recorded {sig.label.lower()}s across {len(intervals)} interval(s).",
        explanation=explanation,
        message=(
            f"{sig.label} recurs about every {_months(mean_interval)} months on {tag}. "
            f"The current cycle is {_months(age_days)} months old, so the next one is projected "
            f"around {center.isoformat()}."
        ),
        evidence=evidence,
        supporting_signals=_supporting_signals(work_orders, {f["wo_id"] for f in failures}),
    )


def get_predictions(tag: str) -> list[PredictionResult]:
    """All failure-type predictions for one asset (empty when no pattern exists)."""
    work_orders = _fetch_work_orders(tag)
    results = []
    for ftype, sig in FAILURE_SIGNATURES.items():
        result = _predict_for_signature(tag, work_orders, ftype, sig)
        if result is not None:
            results.append(result)
    # Worst first so the frontend can lead with the scariest one.
    results.sort(key=lambda r: _RISK_ORDER.get(r.risk_level or "", 0), reverse=True)
    return results


def get_fleet_predictions() -> list[FleetPredictionItem]:
    """One row per asset with its highest current risk, worst first (for the dashboard)."""
    items = []
    with get_driver().session() as session:
        equipment = session.run("MATCH (e:Equipment) RETURN e.tag AS tag, e.name AS name ORDER BY e.tag")
        assets = [(r["tag"], r["name"]) for r in equipment]

    for tag, name in assets:
        predicted = [p for p in get_predictions(tag) if p.status == "predicted"]
        if predicted:
            top = predicted[0]
            items.append(FleetPredictionItem(
                tag=tag, name=name, status="predicted", risk_level=top.risk_level,
                failure_label=top.failure_label, days_until_center=top.days_until_center,
                message=top.message,
            ))
        else:
            items.append(FleetPredictionItem(
                tag=tag, name=name, status="no_prediction",
                message="No recurring failure pattern detected yet.",
            ))

    items.sort(key=lambda i: _RISK_ORDER.get(i.risk_level or "", 0), reverse=True)
    return items


def _fetch_work_orders(tag: str) -> list[dict]:
    """All work orders for an asset with the fields prediction needs."""
    cypher = """
        MATCH (e:Equipment {tag: $tag})-[:HAS_WORKORDER]->(w:WorkOrder)
        RETURN w.wo_id AS wo_id, w.date AS date, w.description AS description, w.status AS status
    """
    with get_driver().session() as session:
        return [r.data() for r in session.run(cypher, tag=tag)]
