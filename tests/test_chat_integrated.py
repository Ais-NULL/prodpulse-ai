"""Real Streamlit form, HTTP, FastAPI and model. Isolate Mongo and Gemini in this test."""
import io
import json
import socket
from datetime import date
from pathlib import Path
from threading import Thread
from time import monotonic, sleep

import pytest
import uvicorn
from streamlit.testing.v1 import AppTest
from shared.contracts import Department


def test_streamlit_to_model_history_and_chat(monkeypatch):
    mongomock = pytest.importorskip("mongomock")
    from backend.app import database
    from backend.app.main import app
    from frontend.api_client import ApiClient

    memory_db = mongomock.MongoClient()
    monkeypatch.setattr(database, "client", lambda: memory_db)
    monkeypatch.setenv("MONGODB_DB_NAME", "integration_test")
    database.ensure_indexes.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "gemini-test")
    monkeypatch.setenv("LLM_API_KEY", "test-only")
    def gemini_reply(request, timeout):
        body = json.loads(request.data)
        assert body["contents"][0]["parts"][0]["text"] == "Tim ini mencapai target?"
        response = {"candidates": [{"content": {"parts": [{"text": '{"topics":["target"]}'}]}}]}
        return io.BytesIO(json.dumps(response).encode())
    monkeypatch.setattr("assistant.gemini.urlopen", gemini_reply)

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="off"))
        thread = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            until = monotonic() + 10
            while not server.started and thread.is_alive() and monotonic() < until:
                sleep(.05)
            assert server.started
            url = f"http://127.0.0.1:{sock.getsockname()[1]}"
            monkeypatch.setenv("API_BASE_URL", url)
            monkeypatch.setenv("PRODPULSE_FRONTEND_MODE", "api")
            client = ApiClient(url)
            assert client.get_health()["status"] == "ok"
            frontend = Path(__file__).resolve().parents[1] / "frontend/app.py"
            ui = AppTest.from_file(str(frontend), default_timeout=15).run()
            ui.switch_page("pages/prediction.py").run()
            ui.date_input(key="production_date").set_value(date(2026, 12, 1))
            ui.selectbox(key="department").select(Department.SEWING)
            for key, value in {"team_id": 3, "target_percent": 80., "smv_minutes": 26.16, "worker_count": 59.}.items():
                ui.number_input(key=key).set_value(value)
            next(b for b in ui.button if b.label == "Buat estimasi").click().run()
            assert not ui.exception
            result = ui.session_state["prediction_result"]
            assert result.predicted_productivity == pytest.approx(.8345914419446663)
            assert client.list_predictions(limit=20, offset=0).items == [result]
            assert client.get_prediction(result.prediction_id) == result
            next(b for b in ui.button if b.label == "Bahas prediksi dengan AI Assistant").click().run()
            ui.switch_page("pages/assistant.py").run()
            ui.chat_input[0].set_value("Tim ini mencapai target?").run()
            assert not ui.exception
            reply = ui.session_state["conversations"][result.prediction_id].turns[-1].response
            assert reply.status == "answered" and reply.evidence[0].id == result.prediction_id
            assert "83.46%" in reply.answer and "3.46 poin persentase di atas" in reply.answer
            saved = memory_db.integration_test.chat_sessions.find_one({"conversation_id": reply.conversation_id})
            assert saved["messages"][0]["prediction_id"] == result.prediction_id
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            database.ensure_indexes.cache_clear()
