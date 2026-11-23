from fastapi import APIRouter
from backend.app.services.analytics_service import overview
from backend.app.services.prediction_service import active_model
from shared.contracts import API_PREFIX, OverviewResponse

router = APIRouter(prefix=API_PREFIX)


@router.get("/analytics/overview", response_model=OverviewResponse)
def get_overview():
    return overview()


@router.get("/models/active")
def get_model():
    meta = active_model()
    return {k: meta[k] for k in ("model_version", "feature_names", "metrics") if k in meta}
