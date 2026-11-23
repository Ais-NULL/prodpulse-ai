"""Tes integrasi / kontrak API ProdPulse AI (Faiz, QA).

Default: berjalan terhadap MOCK API (mock_api/app.py) lewat TestClient,
tanpa server dan tanpa MongoDB.

Untuk menguji backend ASLI Rendi, jalankan servernya lalu:
    PowerShell:  $env:INTEGRATION_API_URL="http://localhost:8000"
                 python -m pytest -q tests/test_integration.py
Tes ditulis relatif (tidak mengandalkan DB kosong) agar berlaku di keduanya.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest

from shared.contracts import (
    API_PREFIX,
    MODEL_FEATURE_NAMES,
    ActiveModelResponse,
    ChatResponse,
    ErrorResponse,
    HealthResponse,
    MetaOptionsResponse,
    OverviewResponse,
    PredictionListResponse,
    PredictionRequest,
    PredictionResponse,
    TeamAnalyticsResponse,
    get_target_comparison,
)

REAL_API_URL = os.getenv("INTEGRATION_API_URL")
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

VALID_PAYLOAD = {
    "production_date": "2026-12-01",
    "department": "sewing",
    "team_id": 3,
    "target_productivity": 0.80,
    "smv_minutes": 26.16,
    "worker_count": 59.0,
}


@pytest.fixture(scope="module")
def client():
    if REAL_API_URL:
        with httpx.Client(base_url=REAL_API_URL, timeout=15) as c:
            yield c
    else:
        from fastapi.testclient import TestClient

        from mock_api.app import app, reset_store

        reset_store()
        with TestClient(app) as c:
            yield c


def create(client, **overrides) -> PredictionResponse:
    resp = client.post(f"{API_PREFIX}/predictions", json={**VALID_PAYLOAD, **overrides})
    assert resp.status_code == 201, resp.text
    return PredictionResponse.model_validate(resp.json())


def assert_error(resp, status: int, code: str) -> ErrorResponse:
    assert resp.status_code == status, resp.text
    err = ErrorResponse.model_validate(resp.json())
    assert err.code == code
    return err


# ------------------------------------------------------- sistem & metadata


def test_health_schema(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    HealthResponse.model_validate(resp.json())


def test_meta_options_schema(client):
    resp = client.get(f"{API_PREFIX}/meta/options")
    assert resp.status_code == 200
    options = MetaOptionsResponse.model_validate(resp.json())
    assert {d.value for d in options.departments} <= {"sewing", "finishing"}


def test_active_model_uses_contract_features(client):
    resp = client.get(f"{API_PREFIX}/models/active")
    assert resp.status_code == 200
    model = ActiveModelResponse.model_validate(resp.json())
    assert tuple(model.feature_names) == MODEL_FEATURE_NAMES


# ------------------------------------------------------------- prediksi


def test_create_prediction_returns_valid_contract(client):
    created = create(client)
    assert created.schema_version == "1.0"
    assert created.prediction_type == "demo_estimate"
    assert created.model_version


def test_create_prediction_echoes_inputs_as_ratio(client):
    created = create(client, target_productivity=0.8)
    # rasio tetap 0.8, tidak boleh berubah menjadi 80
    assert created.target_productivity == 0.8
    assert created.department.value == "sewing"
    assert created.team_id == 3
    assert created.production_date.isoformat() == "2026-12-01"


def test_gap_and_status_follow_contract_formula(client):
    created = create(client, target_productivity=0.9)
    gap, status = get_target_comparison(
        created.predicted_productivity, created.target_productivity
    )
    assert created.gap_percentage_points == pytest.approx(gap, abs=1e-3)
    assert created.target_status == status


def test_get_prediction_roundtrip(client):
    created = create(client)
    resp = client.get(f"{API_PREFIX}/predictions/{created.prediction_id}")
    assert resp.status_code == 200
    assert PredictionResponse.model_validate(resp.json()) == created


def test_get_unknown_prediction_is_404_error_contract(client):
    resp = client.get(f"{API_PREFIX}/predictions/id-yang-tidak-ada")
    assert_error(resp, 404, "not_found")


@pytest.mark.parametrize(
    "bad_payload, bad_field",
    [
        ({"target_productivity": 80}, "target_productivity"),  # persen, bukan rasio
        ({"worker_count": 0}, "worker_count"),
        ({"smv_minutes": -1}, "smv_minutes"),
        ({"team_id": 0}, "team_id"),
        ({"department": "cutting"}, "department"),
        ({"production_date": "01-12-2026"}, "production_date"),
        ({"total_workers": 59.0}, "total_workers"),  # sinonim terlarang
    ],
)
def test_invalid_payload_is_422_with_field(client, bad_payload, bad_field):
    resp = client.post(f"{API_PREFIX}/predictions", json={**VALID_PAYLOAD, **bad_payload})
    err = assert_error(resp, 422, "validation_error")
    assert bad_field in [f.field for f in err.fields]


def test_missing_field_is_422(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "smv_minutes"}
    resp = client.post(f"{API_PREFIX}/predictions", json=payload)
    err = assert_error(resp, 422, "validation_error")
    assert "smv_minutes" in [f.field for f in err.fields]


def test_fractional_worker_count_is_accepted(client):
    created = create(client, worker_count=30.5)
    assert created.prediction_id


# ----------------------------------------------- histori & persistensi


def test_created_prediction_appears_in_history(client):
    before = PredictionListResponse.model_validate(
        client.get(f"{API_PREFIX}/predictions").json()
    ).total
    created = create(client)
    listing = PredictionListResponse.model_validate(
        client.get(f"{API_PREFIX}/predictions", params={"limit": 100}).json()
    )
    assert listing.total == before + 1
    assert created.prediction_id in [i.prediction_id for i in listing.items]


def test_pagination_limit_and_offset(client):
    for _ in range(3):
        create(client)
    first = PredictionListResponse.model_validate(
        client.get(f"{API_PREFIX}/predictions", params={"limit": 2, "offset": 0}).json()
    )
    second = PredictionListResponse.model_validate(
        client.get(f"{API_PREFIX}/predictions", params={"limit": 2, "offset": 2}).json()
    )
    assert first.limit == 2 and first.offset == 0 and len(first.items) == 2
    assert second.offset == 2
    ids_first = {i.prediction_id for i in first.items}
    assert ids_first.isdisjoint({i.prediction_id for i in second.items})


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": -1}, {"offset": -1}])
def test_invalid_pagination_is_422(client, params):
    resp = client.get(f"{API_PREFIX}/predictions", params=params)
    assert_error(resp, 422, "validation_error")


# ------------------------------------------------------------ analytics


def test_overview_separates_historical_from_predictions(client):
    def overview() -> OverviewResponse:
        resp = client.get(f"{API_PREFIX}/analytics/overview")
        assert resp.status_code == 200
        return OverviewResponse.model_validate(resp.json())

    before = overview()
    create(client)
    after = overview()
    assert after.prediction_count == before.prediction_count + 1
    # membuat prediksi TIDAK boleh mengubah jumlah data historis
    assert after.historical_records == before.historical_records


def test_team_analytics_is_historical_and_consistent_with_overview(client):
    resp = client.get(f"{API_PREFIX}/analytics/teams")
    assert resp.status_code == 200
    teams = TeamAnalyticsResponse.model_validate(resp.json())
    assert teams.data_label == "historical_dataset"
    overview = OverviewResponse.model_validate(
        client.get(f"{API_PREFIX}/analytics/overview").json()
    )
    assert sum(t.record_count for t in teams.items) == overview.historical_records


# ----------------------------------------------------------------- chat


def test_chat_with_prediction_cites_evidence(client):
    created = create(client)
    resp = client.post(
        f"{API_PREFIX}/chat",
        json={"message": "Kenapa di bawah target?", "prediction_id": created.prediction_id},
    )
    assert resp.status_code == 200
    chat = ChatResponse.model_validate(resp.json())
    assert chat.status == "answered"
    assert any(e.type == "prediction" and e.id == created.prediction_id for e in chat.evidence)
    assert chat.conversation_id


def test_chat_unknown_prediction_does_not_invent_data(client):
    resp = client.post(
        f"{API_PREFIX}/chat",
        json={"message": "Berapa prediksinya?", "prediction_id": "id-tidak-ada"},
    )
    assert resp.status_code == 200
    chat = ChatResponse.model_validate(resp.json())
    assert chat.status in ("insufficient_data", "unavailable")
    assert chat.evidence == []


def test_chat_keeps_conversation_id(client):
    created = create(client)
    first = ChatResponse.model_validate(
        client.post(
            f"{API_PREFIX}/chat",
            json={"message": "Halo", "prediction_id": created.prediction_id},
        ).json()
    )
    second = ChatResponse.model_validate(
        client.post(
            f"{API_PREFIX}/chat",
            json={
                "message": "Lanjut",
                "prediction_id": created.prediction_id,
                "conversation_id": first.conversation_id,
            },
        ).json()
    )
    assert second.conversation_id == first.conversation_id


@pytest.mark.parametrize("message", ["", "x" * 2001])
def test_chat_message_length_is_validated(client, message):
    resp = client.post(f"{API_PREFIX}/chat", json={"message": message})
    assert_error(resp, 422, "validation_error")


# ------------------------------------------------- contoh JSON di repo


def test_example_files_match_contract():
    request = json.loads((EXAMPLES / "prediction_request.json").read_text(encoding="utf-8"))
    PredictionRequest.model_validate(request)
    response = json.loads(
        (EXAMPLES / "prediction_response_example_only.json").read_text(encoding="utf-8")
    )
    parsed = PredictionResponse.model_validate(response)
    gap, status = get_target_comparison(parsed.predicted_productivity, parsed.target_productivity)
    assert parsed.gap_percentage_points == pytest.approx(gap, abs=1e-3)
    assert parsed.target_status == status
