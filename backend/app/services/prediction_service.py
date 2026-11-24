"""Service prediksi: memanggil model Barra, menghitung selisih, menyimpan ke MongoDB.

Nama fungsi publik yang juga dipakai kode Ardika (routes/chat.py, main.py):
    - get_prediction_by_id
    - active_model
"""
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from backend.app.database import get_db
from ml.inference import predict_productivity
from shared.contracts import PredictionRequest

ROOT = Path(__file__).resolve().parents[3]  # root repo


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def active_model() -> dict:
    """Metadata model aktif (isi metadata.json). Raise HTTP 503 kalau tidak tersedia."""
    artifact = _resolve(os.getenv("MODEL_ARTIFACT_PATH", "ml/artifacts/model.joblib"))
    meta_path = artifact.with_name("metadata.json")
    if not artifact.exists() or not meta_path.exists():
        raise HTTPException(status_code=503, detail="Model tidak tersedia")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except ValueError:
        raise HTTPException(status_code=503, detail="Metadata model tidak valid")
    if "model_version" not in meta:
        raise HTTPException(status_code=503, detail="Metadata model tidak memuat model_version")
    return meta


def create_prediction(req: PredictionRequest) -> dict:
    model_version = active_model()["model_version"]
    predicted = float(predict_productivity(req))  # jangan di-clip diam-diam
    target = req.target_productivity
    gap = (predicted - target) * 100
    status = "below_target" if predicted < target else "meets_or_exceeds_target"

    response = {
        "schema_version": "1.0",
        "prediction_id": str(uuid.uuid4()),
        "model_version": model_version,
        "production_date": req.production_date.isoformat(),
        "department": req.department.value,
        "team_id": req.team_id,
        "target_productivity": target,
        "predicted_productivity": predicted,
        "gap_percentage_points": gap,
        "target_status": status,
        "prediction_type": "demo_estimate",
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    # Disimpan: response + input_snapshot. Dikembalikan ke API: response saja,
    # karena PredictionResponse di kontrak tidak mengizinkan field tambahan.
    stored = {**response, "input_snapshot": req.model_dump(mode="json")}
    get_db().predictions.insert_one(stored)  # _id hanya ditambahkan ke `stored`
    return response


def get_prediction_by_id(prediction_id: str, include_snapshot: bool = False) -> dict | None:
    projection = {"_id": 0} if include_snapshot else {"_id": 0, "input_snapshot": 0}
    return get_db().predictions.find_one({"prediction_id": prediction_id}, projection)


def list_predictions(limit: int = 20, offset: int = 0,
                     department: str | None = None, team_id: int | None = None) -> dict:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    query: dict = {}
    if department:
        query["department"] = department
    if team_id is not None:
        query["team_id"] = team_id

    col = get_db().predictions
    items = list(
        col.find(query, {"_id": 0, "input_snapshot": 0})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    return {"items": items, "total": col.count_documents(query), "limit": limit, "offset": offset}