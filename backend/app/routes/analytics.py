from fastapi import APIRouter

from backend.app.services import analytics_service
from shared.contracts import API_PREFIX, TeamAnalyticsResponse

router = APIRouter(prefix=f"{API_PREFIX}/analytics", tags=["analytics"])


@router.get("/overview")
def overview():
    return analytics_service.overview()


@router.get("/teams", response_model=TeamAnalyticsResponse)
def teams():
    return analytics_service.teams_summary()