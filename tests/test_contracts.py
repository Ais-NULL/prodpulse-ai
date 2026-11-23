from datetime import date

import pytest
from pydantic import ValidationError

from shared.contracts import (
    MODEL_FEATURE_NAMES,
    PredictionRequest,
    TargetStatus,
    get_target_comparison,
)
from shared.normalization import normalize_department, normalize_uci_row, pre_shift_features


def example_request():
    return PredictionRequest(
        production_date="2026-12-01",
        department="sewing",
        team_id=3,
        target_productivity=0.8,
        smv_minutes=26.16,
        worker_count=59.0,
    )


def test_prediction_contract_and_weekday():
    request = example_request()
    assert request.production_date == date(2026, 12, 1)
    assert list(pre_shift_features(request)) == list(MODEL_FEATURE_NAMES)
    assert pre_shift_features(request)["day_of_week"] == 1  # Tuesday


def test_target_units_and_status():
    gap, status = get_target_comparison(0.74, 0.8)
    assert gap == -6.0
    assert status == TargetStatus.BELOW_TARGET


def test_invalid_request_rejected():
    data = example_request().model_dump()
    data["target_productivity"] = 80  # salah: bukan rasio
    with pytest.raises(ValidationError):
        PredictionRequest(**data)


def test_unknown_fields_rejected():
    data = example_request().model_dump()
    data["total_workers"] = 59.0
    with pytest.raises(ValidationError):
        PredictionRequest(**data)


def test_dataset_dept_typo_and_fractional_workers_and_label_over_one():
    row = {
        "date": "1/1/2015",
        "department": " sweing ",
        "team": "8",
        "targeted_productivity": 0.8,
        "smv": 26.16,
        "no_of_workers": 30.5,
        "actual_productivity": 1.120437,
    }
    parsed = normalize_uci_row(row, "uci_597_0")
    assert parsed["department"] == "sewing"
    assert parsed["worker_count"] == 30.5
    assert parsed["actual_productivity"] == 1.120437
    assert parsed["day_of_week"] == 3


def test_normalize_department():
    assert normalize_department("Finishing ").value == "finishing"
