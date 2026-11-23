"""Unit test untuk modul ML dan inference ProdPulse AI."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import joblib
import pandas as pd
import pytest
from sklearn.dummy import DummyRegressor
from sklearn.pipeline import Pipeline

from shared.contracts import Department, MODEL_FEATURE_NAMES, SCHEMA_VERSION, PredictionRequest
from ml.evaluate import evaluate_regression
from ml.feature_pipeline import build_preprocessor, prepare_training_dataframe, request_to_dataframe
from ml.inference import (
    DEFAULT_ARTIFACT_PATH,
    get_active_model_metadata,
    load_model_bundle,
    predict_productivity,
)


def _sample_request() -> PredictionRequest:
    return PredictionRequest(
        production_date=date(2026, 12, 1),  # Selasa -> day_of_week = 1
        department=Department.SEWING,
        team_id=3,
        target_productivity=0.80,
        smv_minutes=26.16,
        worker_count=59.0,
    )


@pytest.fixture
def synthetic_model_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Membuat artefak model sintetis sementara agar test jalan tanpa file model.joblib asli."""
    train_df = pd.DataFrame(
        [
            {
                "department": "sewing",
                "team_id": 3,
                "day_of_week": 1,
                "target_productivity": 0.80,
                "smv_minutes": 26.16,
                "worker_count": 59.0,
                "actual_productivity": 0.78,
            },
            {
                "department": "finishing",
                "team_id": 5,
                "day_of_week": 2,
                "target_productivity": 0.75,
                "smv_minutes": 15.0,
                "worker_count": 20.0,
                "actual_productivity": 0.82,
            },
        ]
    )
    X = prepare_training_dataframe(train_df)
    y = train_df["actual_productivity"].to_numpy(dtype=float)

    pipe = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("regressor", DummyRegressor(strategy="mean")),
        ]
    )
    pipe.fit(X, y)

    model_path = tmp_path / "model.joblib"
    metadata_path = tmp_path / "metadata.json"
    joblib.dump(pipe, model_path)

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "model_version": "synthetic-test-v1",
        "feature_names": list(MODEL_FEATURE_NAMES),
        "metrics": {
            "synthetic-test-v1": {
                "holdout_test": {"mae": 0.05, "rmse": 0.06, "r2": 0.25}
            }
        },
    }
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    import ml.inference as inf

    monkeypatch.setattr(inf, "DEFAULT_ARTIFACT_PATH", model_path)
    monkeypatch.setattr(inf, "DEFAULT_METADATA_PATH", metadata_path)
    monkeypatch.setattr(inf, "_cached_model", None)
    monkeypatch.setattr(inf, "_cached_metadata", None)

    return model_path, metadata_path


def test_request_to_dataframe_matches_contract_features():
    req = _sample_request()
    df = request_to_dataframe(req)

    assert list(df.columns) == list(MODEL_FEATURE_NAMES)
    assert len(df) == 1
    assert df.loc[0, "department"] == "sewing"
    assert df.loc[0, "team_id"] == 3
    assert df.loc[0, "day_of_week"] == 1
    assert df.loc[0, "worker_count"] == 59.0


def test_evaluate_regression_returns_canonical_keys():
    metrics = evaluate_regression([0.8, 0.7], [0.75, 0.72])
    assert set(metrics.keys()) == {"mae", "rmse", "r2"}


def test_predict_productivity_with_synthetic_bundle(synthetic_model_bundle):
    req = _sample_request()
    pred = predict_productivity(req)

    assert isinstance(pred, float)
    assert pred >= 0.0


def test_active_model_metadata_with_synthetic_bundle(synthetic_model_bundle):
    meta = get_active_model_metadata()

    assert meta["schema_version"] == SCHEMA_VERSION
    assert isinstance(meta["model_version"], str) and len(meta["model_version"]) > 0
    assert tuple(meta["feature_names"]) == MODEL_FEATURE_NAMES
    assert "metrics" in meta


@pytest.mark.skipif(
    not DEFAULT_ARTIFACT_PATH.exists(),
    reason="Artefak model.joblib belum di-generate; jalankan `python -m ml.train`.",
)
def test_real_trained_artifact_if_present():
    req = _sample_request()
    pred = predict_productivity(req)
    meta = get_active_model_metadata()

    assert isinstance(pred, float)
    assert pred >= 0.0
    assert meta["schema_version"] == SCHEMA_VERSION
    assert isinstance(meta["model_version"], str) and len(meta["model_version"]) > 0


def test_load_missing_artifact_raises_file_not_found(monkeypatch: pytest.MonkeyPatch):
    import ml.inference as inf

    monkeypatch.setattr(inf, "_cached_model", None)
    monkeypatch.setattr(inf, "_cached_metadata", None)
    with pytest.raises(FileNotFoundError):
        load_model_bundle(model_path=Path("ml/artifacts/tidak_ada.joblib"))