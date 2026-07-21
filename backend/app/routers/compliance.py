"""
Compliance endpoints.

  GET /equipment/{tag}/compliance   findings for one asset
  GET /compliance                   fleet roll-up with per-asset status,
                                    overall counts, and the H/S/E breakdown

Thin layer over compliance_service; the rules and detection live there.
"""

from fastapi import APIRouter

from app.services.compliance_service import (
    ComplianceFinding,
    FleetCompliance,
    evaluate_equipment_compliance,
    evaluate_fleet_compliance,
)

router = APIRouter(tags=["compliance"])


@router.get("/equipment/{tag}/compliance", response_model=list[ComplianceFinding])
def equipment_compliance(tag: str) -> list[ComplianceFinding]:
    return evaluate_equipment_compliance(tag)


@router.get("/compliance", response_model=FleetCompliance)
def fleet_compliance() -> FleetCompliance:
    return evaluate_fleet_compliance()
