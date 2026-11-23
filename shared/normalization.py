"""Normalisasi dataset UCI dan pembuatan input pre-shift bersama."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping

from shared.contracts import Department, MODEL_FEATURE_NAMES, PredictionRequest


def normalize_department(value: str) -> Department:
    cleaned = str(value).strip().lower()
    if cleaned == "sweing":  # typo historis dalam dataset UCI
        cleaned = "sewing"
    return Department(cleaned)


def parse_uci_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    value = str(value).strip()
    # Dataset asal biasanya M/D/YYYY; format ISO juga diterima.
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Format date tidak didukung: {value!r}")


def normalize_uci_row(row: Mapping[str, Any], source_record_id: str) -> dict[str, Any]:
    """Konversi 1 baris UCI ke dokumen DB. Label adalah hasil aktual, bukan fitur prediksi."""
    d = parse_uci_date(row["date"])
    raw_team = float(row["team"])
    if not raw_team.is_integer():
        raise ValueError("team harus bilangan bulat kategorikal")
    return {
        "source_record_id": source_record_id,
        "production_date": d.isoformat(),
        "department": normalize_department(row["department"]).value,
        "team_id": int(raw_team),
        "target_productivity": float(row["targeted_productivity"]),
        "smv_minutes": float(row["smv"]),
        "worker_count": float(row["no_of_workers"]),
        "actual_productivity": float(row["actual_productivity"]),
        "day_of_week": d.weekday(),
        "data_source": "uci_597",
    }


def pre_shift_features(request: PredictionRequest) -> dict[str, Any]:
    """Interface tunggal train/predict — daftar dan urutan kolom tetap."""
    all_features = {
        "department": request.department.value,
        "team_id": request.team_id,
        "target_productivity": request.target_productivity,
        "smv_minutes": request.smv_minutes,
        "worker_count": request.worker_count,
        "day_of_week": request.production_date.weekday(),
    }
    return {name: all_features[name] for name in MODEL_FEATURE_NAMES}
