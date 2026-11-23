"""Sumber baca tunggal untuk prediksi. Backend dapat memasok fungsi dengan bentuk sama."""
import json
from pathlib import Path


def load_demo_reader(path: Path):
    record = json.loads(path.read_text(encoding="utf-8"))

    def get_prediction_by_id(prediction_id: str):
        if prediction_id == record["prediction_id"]:
            return record.copy()
        return None

    return get_prediction_by_id
