"""Opsional: jalankan dari root repo dengan ML tim dan versi library metadata."""
import csv
import hashlib
import json
from pathlib import Path

from ml.feature_pipeline import prepare_training_dataframe
from ml.inference import load_model_bundle
from shared.contracts import PredictionRequest
from shared.normalization import normalize_uci_row, pre_shift_features
import pandas as pd


def main():
    csv_path = Path("data/garments_worker_productivity.csv")
    model_path = Path("ml/artifacts/model.joblib")
    model, metadata = load_model_bundle(model_path=model_path)
    start, end = metadata["split_summary"]["test_date_range"]
    features, identifiers = [], []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for index, row in enumerate(csv.DictReader(f), 1):
            record = normalize_uci_row(row, f"uci_597_{index:04d}")
            if start <= record["production_date"] <= end:
                plan = PredictionRequest(**{k: record[k] for k in PredictionRequest.model_fields})
                features.append(pre_shift_features(plan))
                identifiers.append(record["source_record_id"])
    forecasts = model.predict(prepare_training_dataframe(pd.DataFrame(features)))
    snapshot = {
        "dataset_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "model_version": metadata["model_version"],
        "test_date_range": [start, end],
        "predictions": dict(zip(identifiers, map(float, forecasts), strict=True)),
    }
    Path("data/uci_holdout_predictions.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
