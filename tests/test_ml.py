"""Unit test untuk modul ML dan inference ProdPulse AI."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import pytest

from shared.contracts import Department, MODEL_FEATURE_NAMES, PredictionRequest
from ml.feature_pipeline import request_to_dataframe
from ml.inference import get_active_model_metadata, load_model_bundle, predict_productivity


def _sample_request() -> PredictionRequest:
    return PredictionRequest(
        production_date=date(2026, 12, 1),  # Selasa -> day_of_week = 1
        department=Department.SEWING,
        team_id=3,
        target_productivity=0.80,
        smv_minutes=26.16,
        worker_count=59.0,
    )


def test_request_to_dataframe_matches_contract_features():
    req = _sample_request()
    df = request_to_dataframe(req)

    assert list(df.columns) == list(MODEL_FEATURE_NAMES)
    assert len(df) == 1
    assert df.loc[0, "department"] == "sewing"
    assert df.loc[0, "team_id"] == 3
    assert df.loc[0, "day_of_week"] == 1
    assert df.loc[0, "worker_count"] == 59.0


def test_predict_productivity_returns_valid_float():
    req = _sample_request()
    pred = predict_productivity(req)

    assert isinstance(pred, float)
    assert pred >= 0.0


def test_active_model_metadata_matches_schema_v1():
    meta = get_active_model_metadata()

    assert meta["schema_version"] == "1.0"
    assert meta["model_version"] == "rf-v1"
    assert tuple(meta["feature_names"]) == MODEL_FEATURE_NAMES
    assert "metrics" in meta


def test_load_missing_artifact_raises_file_not_found():
    import ml.inference as inf

    orig_model = inf._cached_model
    try:
        inf._cached_model = None
        with pytest.raises(FileNotFoundError):
            load_model_bundle(model_path=Path("ml/artifacts/tidak_ada.joblib"))
    finally:
        inf._cached_model = orig_model