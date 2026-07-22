"""
Work-order draft endpoints (human-in-the-loop closure of a prediction).

  POST /workorders/draft              build a draft from a prediction
  GET  /workorders/drafts             list drafts
  POST /workorders/drafts/{id}/approve  approve -> creates the open WorkOrder
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import workorder_draft_service
from app.services.workorder_draft_service import WorkOrderDraftOut

router = APIRouter(prefix="/workorders", tags=["workorders"])


class DraftRequest(BaseModel):
    equipment_tag: str
    failure_type: str


@router.post("/draft", response_model=WorkOrderDraftOut)
def create_draft(request: DraftRequest) -> WorkOrderDraftOut:
    draft = workorder_draft_service.draft_from_prediction(request.equipment_tag, request.failure_type)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"No {request.failure_type} prediction for {request.equipment_tag}.")
    return draft


@router.get("/drafts", response_model=list[WorkOrderDraftOut])
def list_drafts() -> list[WorkOrderDraftOut]:
    return workorder_draft_service.list_drafts()


@router.post("/drafts/{draft_id}/approve", response_model=WorkOrderDraftOut)
def approve(draft_id: str) -> WorkOrderDraftOut:
    draft = workorder_draft_service.approve_draft(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Unknown draft: {draft_id}")
    return draft
