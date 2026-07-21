"""
Permit endpoints, including the pre-activation safety check.

  POST /permits/evaluate  run the intervention engine WITHOUT creating a permit
                          (the UI calls this as the operator fills the form)
  POST /permits           create the permit; refuses activation if a critical
                          intervention was not acknowledged
  GET  /permits           list
  GET  /permits/{id}      detail

The acknowledgment check re-evaluates server-side rather than trusting the client,
so a caller cannot skip a warning by omitting it from the request.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import permit_service
from app.services.intervention_service import InterventionResult, evaluate_permit
from app.services.permit_service import PermitOut

router = APIRouter(prefix="/permits", tags=["permits"])


class EvaluateRequest(BaseModel):
    permit_type: str
    equipment_tag: str
    description: str = ""


class CreateRequest(BaseModel):
    permit_type: str
    equipment_tag: str
    description: str = ""
    created_by: str | None = None
    # Ids of the intervention items the operator ticked off.
    acknowledged: list[str] = Field(default_factory=list)


@router.post("/evaluate", response_model=InterventionResult)
def evaluate(request: EvaluateRequest) -> InterventionResult:
    return evaluate_permit(request.permit_type, request.equipment_tag, request.description)


@router.post("", response_model=PermitOut)
def create(request: CreateRequest) -> PermitOut:
    result = evaluate_permit(request.permit_type, request.equipment_tag, request.description)
    acknowledged = set(request.acknowledged)

    # Every critical item that demands acknowledgment must actually be acknowledged.
    missing = [
        item for item in result.items
        if item.severity == "critical" and item.requires_acknowledgment and item.id not in acknowledged
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Critical safety interventions must be acknowledged before activation.",
                "unacknowledged": [item.id for item in missing],
            },
        )

    # Persist only the items the operator actually acknowledged, as audit evidence.
    audit = [item.model_dump() for item in result.items if item.id in acknowledged]
    return permit_service.create_permit(
        permit_type=request.permit_type,
        equipment_tag=request.equipment_tag,
        description=request.description,
        created_by=request.created_by,
        acknowledged_items=audit,
        status="active",
    )


@router.get("", response_model=list[PermitOut])
def list_all() -> list[PermitOut]:
    return permit_service.list_permits()


@router.get("/{permit_id}", response_model=PermitOut)
def detail(permit_id: str) -> PermitOut:
    permit = permit_service.get_permit(permit_id)
    if permit is None:
        raise HTTPException(status_code=404, detail=f"Unknown permit: {permit_id}")
    return permit
