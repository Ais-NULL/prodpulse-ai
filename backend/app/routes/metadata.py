from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/meta", tags=["metadata"])


@router.get("/options")
def get_options():
    return {"departments": ["sewing", "finishing"], "team_ids": list(range(1, 13))}