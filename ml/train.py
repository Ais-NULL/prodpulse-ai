"""Script training & evaluasi kronologis model ProdPulse AI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

from shared.contracts import MODEL_FEATURE_NAMES, SCHEMA_VERSION
from shared.normalization import normalize_uci_row
from ml.evaluate import evaluate_regression
from ml.feature_pipeline import build_preprocessor, prepare_training_dataframe

RAW_CSV_PATH = Path("data/garments_worker_productivity.csv")
ARTIFACT_DIR = Path("ml/artifacts")
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"
RANDOM_STATE = 42


def load_and_normalize_dataset(csv_path: Path = RAW_CSV_PATH) -> pd.DataFrame:
    """Membaca CSV UCI mentah dan menormalisasi tiap baris lewat shared/normalization.py."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset tidak ditemukan di {csv_path}. "
            "Unduh dari UCI (#597) dan simpan sebagai data/garments_worker_productivity.csv"
        )

    raw_df = pd.read_csv(csv_path)
    normalized_rows = []
    for idx, row in raw_df.iterrows():
        source_id = f"uci_597_{idx + 1:04d}"
        normalized_rows.append(normalize_uci_row(row.to_dict(), source_record_id=source_id))

    df = pd.DataFrame(normalized_rows)
    df = df.sort_values(by=["production_date", "department", "team_id"]).reset_index(drop=True)
    return df


def chronological_date_split(
    df: pd.DataFrame, train_ratio: float = 0.70, val_ratio: float = 0.15
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Membagi dataset secara kronologis berdasarkan tanggal unik.
    Semua baris pada tanggal yang sama tetap berada di blok split yang sama.
    """
    unique_dates = sorted(df["production_date"].unique())
    n_dates = len(unique_dates)

    train_end_idx = int(n_dates * train_ratio)
    val_end_idx = int(n_dates * (train_ratio + val_ratio))

    train_dates = set(unique_dates[:train_end_idx])
    val_dates = set(unique_dates[train_end_idx:val_end_idx])
    test_dates = set(unique_dates[val_end_idx:])

    train_df = df[df["production_date"].isin(train_dates)].copy()
    val_df = df[df["production_date"].isin(val_dates)].copy()
    test_df = df[df["production_date"].isin(test_dates)].copy()

    return train_df, val_df, test_df


def train_and_select_model(csv_path: Path = RAW_CSV_PATH) -> dict:
    """Melatih baseline & kandidat regresi, mengevaluasi pada holdout, dan ekspor artefak."""
    df = load_and_normalize_dataset(csv_path)
    train_df, val_df, test_df = chronological_date_split(df)

    X_train = prepare_training_dataframe(train_df)
    y_train = train_df["actual_productivity"].to_numpy(dtype=float)

    X_val = prepare_training_dataframe(val_df)
    y_val = val_df["actual_productivity"].to_numpy(dtype=float)

    X_test = prepare_training_dataframe(test_df)
    y_test = test_df["actual_productivity"].to_numpy(dtype=float)

    candidates = {
        "dummy-mean-v1": DummyRegressor(strategy="mean"),
        "ridge-v1": Ridge(alpha=1.0, random_state=RANDOM_STATE),
        "rf-v1": RandomForestRegressor(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }

    results = {}
    fitted_pipelines = {}

    for name, estimator in candidates.items():
        pipe = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor()),
                ("regressor", estimator),
            ]
        )
        pipe.fit(X_train, y_train)
        val_preds = pipe.predict(X_val)
        val_metrics = evaluate_regression(y_val, val_preds)

        results[name] = {"validation": val_metrics}
        fitted_pipelines[name] = pipe

    # Pilih kandidat ML utama berdasarkan validation RMSE terendah (antara ridge-v1 dan rf-v1)
    ml_candidates = ["ridge-v1", "rf-v1"]
    best_model_name = min(ml_candidates, key=lambda m: results[m]["validation"]["rmse"])

    # Latih ulang model terpilih pada gabungan train + val sebelum evaluasi final di holdout test
    train_val_df = pd.concat([train_df, val_df], ignore_index=True)
    X_train_val = prepare_training_dataframe(train_val_df)
    y_train_val = train_val_df["actual_productivity"].to_numpy(dtype=float)

    final_pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("regressor", candidates[best_model_name]),
        ]
    )
    final_pipeline.fit(X_train_val, y_train_val)

    # Evaluasi semua kandidat di holdout test untuk laporan perbandingan jurnal
    for name, pipe in fitted_pipelines.items():
        eval_pipe = final_pipeline if name == best_model_name else pipe
        test_preds = eval_pipe.predict(X_test)
        results[name]["holdout_test"] = evaluate_regression(y_test, test_preds)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, MODEL_PATH)

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "model_version": best_model_name,
        "feature_names": list(MODEL_FEATURE_NAMES),
        "random_state": RANDOM_STATE,
        "library_versions": {
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "split_summary": {
            "total_records": len(df),
            "train_records": len(train_df),
            "val_records": len(val_df),
            "test_records": len(test_df),
            "train_date_range": [train_df["production_date"].min(), train_df["production_date"].max()],
            "val_date_range": [val_df["production_date"].min(), val_df["production_date"].max()],
            "test_date_range": [test_df["production_date"].min(), test_df["production_date"].max()],
        },
        "metrics": results,
        "training_cutoff": val_df["production_date"].max(),
        "artifact_path": str(MODEL_PATH.as_posix()),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Training selesai. Model terpilih: {best_model_name}")
    print(json.dumps(results, indent=2))
    return metadata


if __name__ == "__main__":
    train_and_select_model()