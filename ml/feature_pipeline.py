"""Feature pipeline tunggal untuk training dan inference ProdPulse AI."""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from shared.contracts import MODEL_FEATURE_NAMES, PredictionRequest
from shared.normalization import pre_shift_features

CATEGORICAL_FEATURES = ["department", "team_id", "day_of_week"]
NUMERIC_FEATURES = ["target_productivity", "smv_minutes", "worker_count"]


def build_preprocessor() -> ColumnTransformer:
    """Membangun ColumnTransformer yang hanya di-fit pada training split."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, NUMERIC_FEATURES),
            ("cat", categorical_transformer, CATEGORICAL_FEATURES),
        ]
    )


def prepare_training_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Memastikan urutan dan tipe data 6 fitur MVP sesuai kontrak."""
    out = df.copy()
    out["department"] = out["department"].astype(str)
    out["team_id"] = out["team_id"].astype(int)
    out["day_of_week"] = out["day_of_week"].astype(int)
    out["target_productivity"] = out["target_productivity"].astype(float)
    out["smv_minutes"] = out["smv_minutes"].astype(float)
    out["worker_count"] = out["worker_count"].astype(float)
    return out[list(MODEL_FEATURE_NAMES)]


def request_to_dataframe(request: PredictionRequest) -> pd.DataFrame:
    """Konversi PredictionRequest v1 ke DataFrame 1 baris untuk inference."""
    features = pre_shift_features(request)
    df = pd.DataFrame([features])
    return prepare_training_dataframe(df)