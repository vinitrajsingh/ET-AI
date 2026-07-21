"""
Prediction endpoints.

  GET /equipment/{tag}/prediction   interval-statistics predictions for one asset
  GET /predictions                  fleet roll-up, highest risk first

Thin layer over prediction_service; all the arithmetic lives there. No LLM.
"""

from fastapi import APIRouter

from app.services.prediction_service import (
    FleetPredictionItem,
    PredictionResult,
    get_fleet_predictions,
    get_predictions,
)

router = APIRouter(tags=["prediction"])


@router.get("/equipment/{tag}/prediction", response_model=list[PredictionResult])
def equipment_prediction(tag: str) -> list[PredictionResult]:
    # Empty list means no recurring pattern for this asset, which the UI shows as
    # an honest "nothing to predict yet" rather than a fabricated number.
    return get_predictions(tag)


@router.get("/predictions", response_model=list[FleetPredictionItem])
def fleet_predictions() -> list[FleetPredictionItem]:
    return get_fleet_predictions()
