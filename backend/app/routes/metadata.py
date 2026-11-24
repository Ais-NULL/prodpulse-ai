from fastapi import APIRouter

from backend.app.database import get_db
from backend.app.services.prediction_service import active_model
from shared.contracts import API_PREFIX, Department

router = APIRouter(prefix=API_PREFIX, tags=["metadata"])


@router.get("/meta/options")
def options():
    team_ids = sorted(get_db().production_records.distinct("team_id"))
    if not team_ids:
        # Data historis belum diimpor. Dataset UCI #597 memakai tim 1-12;
        # sesuaikan bila kontrak menentukan lain.
        team_ids = list(range(1, 13))
    return {"departments": [d.value for d in Department], "team_ids": team_ids}


@router.get("/models/active")
def models_active():
    return active_model()  # isi metadata.json; 503 kalau model tidak tersedia