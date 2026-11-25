"""End-to-end integration tests across FastAPI, ML inference, persistence, and Chat."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from backend.app.main import app


@pytest.fixture
def integration_client(memory_db):
    with TestClient(app) as client:
        yield client


def test_health_and_active_model_integration(integration_client):
    client = integration_client

    health_res = client.get("/health")
    assert health_res.status_code == 200
    body = health_res.json()
    assert body["db_status"] == "ok"
    assert body["model_status"] == "ok"
    assert body["status"] == "ok"

    model_res = client.get("/api/v1/models/active")
    assert model_res.status_code == 200
    model_data = model_res.json()
    assert model_data["model_version"] == "rf-v1"
    assert "feature_names" in model_data


def test_e2e_prediction_persistence_and_chat_flow(integration_client):
    client = integration_client

    # 1. Buat prediksi nyata lewat POST /api/v1/predictions (FastAPI -> ML Barra -> DB)
    payload = {
        "production_date": "2026-12-01",
        "department": "sewing",
        "team_id": 3,
        "target_productivity": 0.80,
        "smv_minutes": 26.16,
        "worker_count": 59.0,
    }
    create_res = client.post("/api/v1/predictions", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()

    assert created["schema_version"] == "1.0"
    assert created["model_version"] == "rf-v1"
    assert created["department"] == "sewing"
    assert created["team_id"] == 3
    assert isinstance(created["predicted_productivity"], float)

    expected_gap = round((created["predicted_productivity"] - 0.80) * 100, 4)
    assert pytest.approx(created["gap_percentage_points"], rel=1e-3) == expected_gap
    expected_status = (
        "below_target"
        if created["predicted_productivity"] < 0.80
        else "meets_or_exceeds_target"
    )
    assert created["target_status"] == expected_status

    prediction_id = created["prediction_id"]

    # 2. Verifikasi persistence lewat GET /api/v1/predictions/{prediction_id} & list
    get_res = client.get(f"/api/v1/predictions/{prediction_id}")
    assert get_res.status_code == 200
    assert get_res.json()["prediction_id"] == prediction_id

    list_res = client.get("/api/v1/predictions?limit=10&offset=0")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["prediction_id"] == prediction_id for item in list_data["items"])

    # 3. Verifikasi integrasi Chatbot (Ardika) membaca prediksi tersimpan tanpa API key berbayar
    with patch.dict("os.environ", {"LLM_API_KEY": ""}):
        chat_res = client.post(
            "/api/v1/chat",
            json={
                "message": "Jelaskan hasil prediksi tim ini",
                "prediction_id": prediction_id,
            },
        )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert chat_data["status"] == "unavailable"
    assert "conversation_id" in chat_data


def test_validation_error_returns_422(integration_client):
    client = integration_client

    invalid_payload = {
        "production_date": "2026-12-01",
        "department": "sewing",
        "team_id": 0,  # invalid: harus >= 1
        "target_productivity": 1.5,  # invalid: harus <= 1.0
        "smv_minutes": -5.0,  # invalid: harus > 0
        "worker_count": 0,  # invalid: harus > 0
    }
    res = client.post("/api/v1/predictions", json=invalid_payload)
    assert res.status_code == 422


def test_database_failure_returns_503(monkeypatch):
    from backend.app import database

    def offline(*args, **kwargs):
        raise PyMongoError("Simulated connection failure")

    monkeypatch.setattr(database, "_client", None)
    monkeypatch.setattr(database, "MongoClient", offline)
    with TestClient(app, raise_server_exceptions=False) as client:
        health_res = client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["db_status"] == "unavailable"
        assert health_res.json()["status"] == "degraded"

        res = client.post(
            "/api/v1/predictions",
            json={
                "production_date": "2026-12-01",
                "department": "sewing",
                "team_id": 3,
                "target_productivity": 0.80,
                "smv_minutes": 26.16,
                "worker_count": 59.0,
            },
        )
        assert res.status_code == 503
