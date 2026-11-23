from fastapi import APIRouter, HTTPException, Query
from backend.app.services import prediction_service as service
from shared.contracts import API_PREFIX, PredictionRequest, PredictionResponse, PredictionListResponse

router = APIRouter(prefix=f"{API_PREFIX}/predictions", tags=["predictions"])


@router.post("", response_model=PredictionResponse, status_code=201)
def create(body: PredictionRequest):
    return service.create_prediction(body)


@router.get("", response_model=PredictionListResponse)
def list_predictions(limit: int = Query(20, ge=1, le=500), offset: int = Query(0, ge=0)):
    return service.list_saved(limit, offset)


@router.get("/{prediction_id}", response_model=PredictionResponse)
def read(prediction_id: str):
    record = service.get_prediction_by_id(prediction_id)
    if record is None:
        raise HTTPException(404, "Prediksi belum ditemukan.")
    return record
