from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from pymongo import DESCENDING
from shared.contracts import PredictionRequest, PredictionResponse, get_target_comparison
from ml.inference import get_active_model_metadata, predict_productivity
from backend.app.database import get_db, ensure_indexes

PUBLIC = {key: 1 for key in PredictionResponse.model_fields}
PUBLIC["_id"] = 0


def active_model():
    try:
        metadata = get_active_model_metadata()
        if not metadata.get("model_version"):
            raise ValueError("missing model_version")
        return metadata
    except Exception as exc:
        raise HTTPException(503, "Model atau metadata tidak dapat dimuat.") from exc


def create_prediction(plan: PredictionRequest):
    metadata = active_model()
    try:
        estimate = predict_productivity(plan)
    except Exception as exc:
        raise HTTPException(503, "Inferensi model gagal.") from exc
    gap, status = get_target_comparison(estimate, plan.target_productivity)
    result = PredictionResponse(
        prediction_id=str(uuid4()), created_at=datetime.now(timezone.utc),
        production_date=plan.production_date, department=plan.department,
        team_id=plan.team_id, target_productivity=plan.target_productivity,
        predicted_productivity=estimate, gap_percentage_points=gap,
        target_status=status, model_version=metadata["model_version"],
    )
    ensure_indexes()
    document = result.model_dump(mode="json")
    document["input_snapshot"] = plan.model_dump(mode="json")
    get_db().predictions.insert_one(document)
    return result


def get_prediction_by_id(prediction_id):
    return get_db().predictions.find_one({"prediction_id": prediction_id}, PUBLIC)


def list_saved(limit, offset):
    collection = get_db().predictions
    rows = collection.find({}, PUBLIC).sort([("created_at", DESCENDING), ("prediction_id", DESCENDING)])
    return dict(items=list(rows.skip(offset).limit(limit)), total=collection.count_documents({}),
                limit=limit, offset=offset)
