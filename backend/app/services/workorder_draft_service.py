"""
Work-order drafts: turn a prediction into a pre-filled work order for approval.

This closes the loop the prediction opened. We pre-fill from the prediction and
the real past work orders on the same failure (parts, task), never inventing parts
or costs that have no basis. A person approves the draft; only then does it become
an open WorkOrder in the graph, so it shows up on the asset's timeline.
"""

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.db.neo4j_client import get_driver
from app.db.postgres import Base, SessionLocal, engine
from app.models.workorder_draft import WorkOrderDraft
from app.services.prediction_service import get_predictions

# Prediction risk maps to work-order priority. Explicit, not a magic formula.
_RISK_TO_PRIORITY = {"High": "Critical", "Elevated": "High", "Watch": "Medium", "Low": "Low"}
# A readable task per failure type; extend alongside the prediction signatures.
_FAILURE_TASK = {"bearing": "Replace drive-end bearing and inspect housing"}


class WorkOrderDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    draft_id: str
    equipment_tag: str
    failure_type: str
    task: str
    trade: str | None = None
    priority: str | None = None
    parts_suggested: str | None = None
    target_date: str | None = None
    justification: dict = {}
    status: str
    approved_wo_id: str | None = None


def init_workorder_storage() -> None:
    Base.metadata.create_all(engine, tables=[WorkOrderDraft.__table__])


def draft_from_prediction(tag: str, failure_type: str) -> WorkOrderDraftOut | None:
    """
    Build a draft from the current prediction for this asset and failure type.
    Returns None when there is no such prediction, rather than guessing one.
    """
    prediction = next(
        (p for p in get_predictions(tag) if p.failure_type == failure_type and p.status == "predicted"),
        None,
    )
    if prediction is None:
        return None

    # Parts come straight from the most recent matching failure, not from thin air.
    latest_wo = prediction.evidence[-1].wo_id if prediction.evidence else None
    parts = _parts_from_work_order(latest_wo) if latest_wo else None

    draft = WorkOrderDraft(
        draft_id="WOD-" + uuid.uuid4().hex[:6].upper(),
        equipment_tag=tag,
        failure_type=failure_type,
        task=f"{_FAILURE_TASK.get(failure_type, failure_type)} on {tag}.",
        trade="Rotating Equipment" if failure_type == "bearing" else None,
        priority=_RISK_TO_PRIORITY.get(prediction.risk_level or "", "Medium"),
        parts_suggested=parts,
        target_date=prediction.predicted_center,
        justification={
            "prediction": prediction.explanation,
            "risk_level": prediction.risk_level,
            "confidence": prediction.confidence,
            "evidence_work_orders": [e.wo_id for e in prediction.evidence],
            "predicted_window": [prediction.predicted_window_start, prediction.predicted_window_end],
        },
        status="draft",
    )
    with SessionLocal() as db:
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return WorkOrderDraftOut.model_validate(draft)


def list_drafts() -> list[WorkOrderDraftOut]:
    from sqlalchemy import select

    with SessionLocal() as db:
        rows = db.execute(select(WorkOrderDraft).order_by(WorkOrderDraft.created_date.desc())).scalars().all()
        return [WorkOrderDraftOut.model_validate(d) for d in rows]


def get_draft(draft_id: str) -> WorkOrderDraftOut | None:
    with SessionLocal() as db:
        draft = db.get(WorkOrderDraft, draft_id)
        return WorkOrderDraftOut.model_validate(draft) if draft else None


def approve_draft(draft_id: str) -> WorkOrderDraftOut | None:
    """Approve a draft: create the open WorkOrder in the graph and mark it approved."""
    with SessionLocal() as db:
        draft = db.get(WorkOrderDraft, draft_id)
        if draft is None:
            return None
        if draft.status == "approved":
            return WorkOrderDraftOut.model_validate(draft)

        wo_id = "WO-" + uuid.uuid4().hex[:5].upper()
        _create_work_order_node(wo_id, draft)

        draft.status = "approved"
        draft.approved_wo_id = wo_id
        db.commit()
        db.refresh(draft)
        return WorkOrderDraftOut.model_validate(draft)


def _create_work_order_node(wo_id: str, draft: WorkOrderDraft) -> None:
    """MERGE the approved work order into the graph so it lands on the timeline."""
    cypher = """
        MERGE (w:WorkOrder {wo_id: $wo_id})
        SET w.date = $date, w.wo_type = 'Corrective', w.status = 'Open',
            w.description = $description, w.parts_used = $parts, w.technician = 'Unassigned',
            w.source_doc = 'prediction-draft'
        WITH w
        MATCH (e:Equipment {tag: $tag})
        MERGE (e)-[:HAS_WORKORDER]->(w)
    """
    with get_driver().session() as session:
        session.run(
            cypher, wo_id=wo_id, tag=draft.equipment_tag,
            date=draft.target_date or date.today().isoformat(),
            description=f"{draft.task} Raised from prediction {draft.draft_id}.",
            parts=draft.parts_suggested,
        )


def _parts_from_work_order(wo_id: str) -> str | None:
    with get_driver().session() as session:
        record = session.run("MATCH (w:WorkOrder {wo_id: $id}) RETURN w.parts_used AS parts", id=wo_id).single()
        return record["parts"] if record else None
