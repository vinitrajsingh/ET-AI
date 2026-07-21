"""
Equipment 360 endpoints.

  GET /equipment          list of all equipment for the landing grid
  GET /equipment/{tag}    the full 360 "biography" for one asset

Thin layer over equipment_service; the graph queries live there.
"""

from fastapi import APIRouter, HTTPException

from app.services.equipment_service import (
    Equipment360Response,
    EquipmentListItem,
    get_equipment_360,
    list_equipment,
)

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("", response_model=list[EquipmentListItem])
def get_equipment_list() -> list[EquipmentListItem]:
    return list_equipment()


@router.get("/{tag}", response_model=Equipment360Response)
def get_equipment_biography(tag: str) -> Equipment360Response:
    result = get_equipment_360(tag)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown equipment tag: {tag}")
    return result
