from fastapi import APIRouter, HTTPException

from shared.contracts import PredictionRequest, PredictionResponse, PredictionListResponse
from backend.app.services import prediction_service

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.post("", response_model=PredictionResponse, status_code=201)
def create_prediction(req: PredictionRequest):
    try:
        return prediction_service.create_prediction(req)
    except (FileNotFoundError, RuntimeError):
        raise HTTPException(503, "Model tidak tersedia")


@router.get("/{prediction_id}", response_model=PredictionResponse)
def get_prediction(prediction_id: str):
    doc = prediction_service.get_prediction_by_id(prediction_id)
    if doc is None:
        raise HTTPException(404, "Prediction tidak ditemukan")
    return doc


@router.get("", response_model=PredictionListResponse)
def list_predictions(limit: int = 20, offset: int = 0):
    return prediction_service.list_predictions(limit=limit, offset=offset)