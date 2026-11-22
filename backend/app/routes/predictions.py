from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("")
def list_predictions(limit: int = 20, offset: int = 0):
    return {"items": [], "total": 0, "limit": limit, "offset": offset}