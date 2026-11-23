"""Inference interface ProdPulse AI — dikonsumsi oleh Backend (Rendi)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import joblib

from shared.contracts import PredictionRequest
from ml.feature_pipeline import request_to_dataframe

DEFAULT_ARTIFACT_PATH = Path(os.getenv("MODEL_ARTIFACT_PATH", "ml/artifacts/model.joblib"))
DEFAULT_METADATA_PATH = Path("ml/artifacts/metadata.json")

_cached_model = None
_cached_metadata = None


def load_model_bundle(
    model_path: Path | None = None,
    metadata_path: Path | None = None,
):
    """Memuat model dan metadata ke memori (lazy loading)."""
    global _cached_model, _cached_metadata
    resolved_model_path = model_path or DEFAULT_ARTIFACT_PATH
    resolved_metadata_path = metadata_path or DEFAULT_METADATA_PATH

    if _cached_model is None:
        if not resolved_model_path.exists():
            raise FileNotFoundError(
                f"Artefak model tidak ditemukan di {resolved_model_path}. "
                "Jalankan `python -m ml.train` terlebih dahulu."
            )
        _cached_model = joblib.load(resolved_model_path)

    if _cached_metadata is None and resolved_metadata_path.exists():
        with open(resolved_metadata_path, "r", encoding="utf-8") as f:
            _cached_metadata = json.load(f)

    return _cached_model, _cached_metadata


def get_active_model_metadata() -> dict:
    """Mengembalikan metadata model aktif untuk endpoint GET /api/v1/models/active."""
    _, metadata = load_model_bundle()
    return metadata or {}


def predict_productivity(request: PredictionRequest) -> float:
    """
    Kontrak utama: menerima PredictionRequest v1 dan mengembalikan rasio produktivitas (float).
    Nilai output tidak di-clip secara diam-diam sesuai aturan kontrak.
    """
    model, _ = load_model_bundle()
    input_df = request_to_dataframe(request)
    pred = model.predict(input_df)[0]
    return float(pred)