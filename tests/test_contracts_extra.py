"""Tes untuk schema tambahan kontrak v1.0 (Faiz)."""

from typing import get_args

import pytest
from pydantic import ValidationError

from shared.contracts import (
    ERROR_HTTP_STATUS,
    MODEL_FEATURE_NAMES,
    ActiveModelResponse,
    ActualRequest,
    ErrorCode,
    ErrorResponse,
    HealthResponse,
    MetaOptionsResponse,
    TeamAnalyticsResponse,
)


def test_every_error_code_has_http_status():
    assert set(get_args(ErrorCode)) == set(ERROR_HTTP_STATUS)
    assert ERROR_HTTP_STATUS["validation_error"] == 422
    assert ERROR_HTTP_STATUS["model_unavailable"] == 503


def test_error_response_forbids_unknown_fields():
    ok = ErrorResponse(code="not_found", message="x")
    assert ok.fields == []
    with pytest.raises(ValidationError):
        ErrorResponse(code="not_found", message="x", detail="synonym")
    with pytest.raises(ValidationError):
        ErrorResponse(code="unknown_code", message="x")


def test_health_status_values():
    HealthResponse(status="ok", db_status="mock", model_status="mock")
    with pytest.raises(ValidationError):
        HealthResponse(status="fine", db_status="ok", model_status="ok")


def test_active_model_features_must_match_contract():
    ActiveModelResponse(model_version="rf-v1", feature_names=list(MODEL_FEATURE_NAMES))
    with pytest.raises(ValidationError):
        ActiveModelResponse(model_version="rf-v1", feature_names=["smv"])
    # urutan juga harus sama
    with pytest.raises(ValidationError):
        ActiveModelResponse(
            model_version="rf-v1", feature_names=list(reversed(MODEL_FEATURE_NAMES))
        )


def test_metrics_default_is_null_not_zero():
    model = ActiveModelResponse(model_version="x", feature_names=list(MODEL_FEATURE_NAMES))
    assert model.metrics is None


def test_meta_options_rejects_bad_team_id():
    MetaOptionsResponse(departments=["sewing"], team_ids=[1, 2])
    with pytest.raises(ValidationError):
        MetaOptionsResponse(departments=["sewing"], team_ids=[0])
    with pytest.raises(ValidationError):
        MetaOptionsResponse(departments=[], team_ids=[1])


def test_team_analytics_is_labeled_historical():
    assert TeamAnalyticsResponse(items=[]).data_label == "historical_dataset"


def test_actual_may_exceed_one_but_not_negative():
    assert ActualRequest(prediction_id="p1", actual_productivity=1.12).actual_productivity == 1.12
    with pytest.raises(ValidationError):
        ActualRequest(prediction_id="p1", actual_productivity=-0.1)
