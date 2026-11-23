"""End-to-end integration tests across FastAPI, ML inference, persistence, and Chat."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import PyMongoError

from backend.app.main import app


class _InMemoryCollection:
    """Minimal MongoDB collection double to verify end-to-end persistence."""

    def __init__(self) -> None:
        self.docs: list[dict] = []

    def insert_one(self, doc: dict):
        self.docs.append(dict(doc))
        return SimpleNamespace(inserted_id=doc.get("prediction_id"))

    def find_one(self, query: dict, projection: dict | None = None):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                result = dict(doc)
                if projection and projection.get("_id") == 0:
                    result.pop("_id", None)
                return result
        return None

    def count_documents(self, query: dict) -> int:
        return sum(1 for d in self.docs if all(d.get(k) == v for k, v in query.items()))

    def find(self, query: dict | None = None, projection: dict | None = None):
        query = query or {}
        matched = [
            dict(d)
            for d in self.docs
            if all(d.get(k) == v for k, v in query.items())
        ]
        return _InMemoryCursor(matched)

    def create_index(self, *args, **kwargs):
        return "mock_index"


class _InMemoryCursor:
    def __init__(self, items: list[dict]) -> None:
        self._items = items

    def sort(self, key: str, direction: int = -1):
        reverse = direction < 0
        self._items.sort(key=lambda x: x.get(key, ""), reverse=reverse)
        return self

    def skip(self, n: int):
        self._items = self._items[n:]
        return self

    def limit(self, n: int):
        self._items = self._items[:n]
        return self

    def __iter__(self):
        return iter(self._items)


class _FakeDatabase:
    def __init__(self) -> None:
        self._collections: dict[str, _InMemoryCollection] = {}

    def __getitem__(self, name: str) -> _InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = _InMemoryCollection()
        return self._collections[name]

    def __getattr__(self, name: str) -> _InMemoryCollection:
        return self[name]

    def command(self, cmd: str):
        if cmd == "ping":
            return {"ok": 1.0}
        raise ValueError(f"Unsupported command: {cmd}")


@pytest.fixture
def integration_client():
    fake_db = _FakeDatabase()
    with (
        patch("backend.app.main.get_db", return_value=fake_db),
        patch("backend.app.database.get_db", return_value=fake_db),
    ):
        with TestClient(app) as client:
            yield client, fake_db


def test_health_and_active_model_integration(integration_client):
    client, _ = integration_client

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
    client, _ = integration_client

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
    assert chat_data["status"] in {"answered", "unavailable"}
    assert "conversation_id" in chat_data


def test_validation_error_returns_422(integration_client):
    client, _ = integration_client

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


def test_database_failure_returns_503():
    import backend.app.services.prediction_service as pred_svc

    def _broken_db():
        raise PyMongoError("Simulated connection failure")

    patches = [
        patch("backend.app.main.get_db", side_effect=_broken_db),
        patch("backend.app.database.get_db", side_effect=_broken_db),
    ]
    if hasattr(pred_svc, "get_db"):
        patches.append(patch.object(pred_svc, "get_db", side_effect=_broken_db))

    with patches[0], patches[1]:
        ctx = patches[2] if len(patches) > 2 else patch("os.getpid")
        with ctx, TestClient(app, raise_server_exceptions=False) as client:
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