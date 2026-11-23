import json
import os
import uuid
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

from backend.app.database import get_db                     # SESUAIKAN: cek nama fungsinya
from shared.contracts import PredictionRequest              # SESUAIKAN: cek nama kelasnya
from ml.inference import predict_productivity               # SESUAIKAN: cek nama fungsi Barra


@cache
def get_model_version() -> str:
    artifact = Path(os.getenv("MODEL_ARTIFACT_PATH", "ml/artifacts/model.joblib"))
    meta = json.loads(artifact.with_name("metadata.json").read_text(encoding="utf-8"))
    return meta["model_version"]                            # SESUAIKAN: key sesuai metadata.json


def create_prediction(req: PredictionRequest) -> dict:
    predicted = float(predict_productivity(req))            # jangan di-clip diam-diam
    target = req.target_productivity
    gap = (predicted - target) * 100
    status = "below_target" if predicted < target else "meets_or_exceeds_target"

    response = {
        "schema_version": "1.0",
        "prediction_id": str(uuid.uuid4()),
        "model_version": get_model_version(),
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
    # Disimpan: response + input_snapshot. Dikembalikan ke API: response saja.
    stored = {**response, "input_snapshot": req.model_dump(mode="json")}
    get_db().predictions.insert_one(stored)   # insert_one menambah _id ke `stored`, bukan ke `response`
    return response


def get_prediction_by_id(prediction_id: str, include_snapshot: bool = False) -> dict | None:
    projection = {"_id": 0} if include_snapshot else {"_id": 0, "input_snapshot": 0}
    return get_db().predictions.find_one({"prediction_id": prediction_id}, projection)


def list_predictions(limit: int = 20, offset: int = 0) -> dict:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    col = get_db().predictions
    items = list(
        col.find({}, {"_id": 0, "input_snapshot": 0})
        .sort("created_at", -1).skip(offset).limit(limit)
    )
    return {"items": items, "total": col.count_documents({}), "limit": limit, "offset": offset}