"""Contract-driven Streamlit smoke tests using stubbed HTTP responses."""

import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
import requests
from streamlit.testing.v1 import AppTest

from frontend.api_client import ApiClient, ApiError
from frontend.formatters import format_gap, format_ratio
from shared.contracts import API_PREFIX, Department, PredictionRequest

ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = f"{API_PREFIX}/predictions"
OVERVIEW = f"{API_PREFIX}/analytics/overview"
CHAT = f"{API_PREFIX}/chat"
BASE_URL = "http://prodpulse.test:8000"


def read_example(name):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


@pytest.fixture
def prediction_fixture():
    return read_example("prediction_response_example_only.json")


@pytest.fixture
def transport(monkeypatch):
    routes = {
        ("GET", "/health"): (200, {"status": "ok", "db_status": "available", "model_status": "ready"}),
        ("GET", OVERVIEW): (200, {
            "historical_records": 1197, "prediction_count": 0, "mean_historical_productivity": 1.12,
        }),
        ("GET", f"{API_PREFIX}/models/active"): (200, {"model_version": "rf-v1"}),
    }
    calls = []

    def request(method, url, **kwargs):
        assert url.startswith(BASE_URL)
        key = (method, urlsplit(url).path)
        calls.append((key, kwargs))
        reply = routes[key]
        if isinstance(reply, Exception):
            raise reply
        status, body = reply(kwargs) if callable(reply) else reply
        return SimpleNamespace(status_code=status, json=lambda: body)

    monkeypatch.setenv("PRODPULSE_FRONTEND_MODE", "api")
    monkeypatch.setenv("API_BASE_URL", BASE_URL)
    monkeypatch.setattr("frontend.api_client.requests.request", request)
    return routes, calls


def open_app(page="overview"):
    app = AppTest.from_file(str(ROOT / "frontend" / "app.py"), default_timeout=10).run()
    assert not app.exception
    if page != "overview":
        app.switch_page(f"pages/{page}.py").run()
        assert not app.exception
    return app


def html(app):
    return "\n".join(element.proto.body for element in app.get("html"))


def button(app, label):
    return next(widget for widget in app.button if widget.label == label)


def fill_prediction(app):
    app.date_input(key="production_date").set_value(date(2026, 12, 1))
    app.selectbox(key="department").select(Department.SEWING)
    for key, value in {
        "team_id": 3, "target_percent": 80.0, "smv_minutes": 26.16, "worker_count": 30.5
    }.items():
        app.number_input(key=key).set_value(value)


def test_formatting_keeps_units_and_values_above_one():
    assert format_ratio(0.74) == "74.0%"
    assert format_ratio(1.204) == "120.4%"
    assert format_ratio(None) == "—"
    assert format_gap(-6.0) == "-6.0 pp"
    assert format_gap(6.0) == "+6.0 pp"
    assert format_gap(-0.0) == "0.0 pp"


def test_overview_uses_api_counts_and_degraded_health(transport):
    routes, _ = transport
    routes[("GET", "/health")] = (503, {
        "status": "degraded", "db_status": "disconnected", "model_status": "unavailable"
    })
    app = open_app()
    markup = html(app)
    for text in ("1.197", "112.0%", "disconnected", "unavailable", "degraded"):
        assert text in markup
    assert "MOCK DATA" not in markup
    assert markup.count('<div class="pp-kpi">') == 4
    assert "Belum ada prediksi tersimpan untuk membuat tren estimasi" in markup
    assert not app.get("plotly_chart")


def test_overview_aggregates_saved_estimates_by_date_and_department_team(transport, prediction_fixture):
    routes, calls = transport
    routes[("GET", OVERVIEW)] = (200, {
        "historical_records": 150, "prediction_count": 3, "mean_historical_productivity": 0.61,
    })
    routes[("GET", PREDICTIONS)] = (200, {
        "items": [
            {**prediction_fixture, "predicted_productivity": 0.84},
            {**prediction_fixture, "prediction_id": "earlier1", "production_date": "2026-11-01",
             "predicted_productivity": 0.64},
            {**prediction_fixture, "prediction_id": "earlier2", "production_date": "2026-11-01",
             "department": "finishing", "predicted_productivity": 0.44},
        ],
        "total": 3, "limit": 12, "offset": 0,
    })
    app = open_app()
    trend, teams = [json.loads(chart.proto.spec)["data"][0] for chart in app.get("plotly_chart")]
    assert trend["x"] == ["2026-11-01", "2026-12-01"]
    assert trend["y"] == pytest.approx([0.54, 0.84])
    assert teams["x"] == ["Finishing 3", "Sewing 3"]
    assert teams["y"] == pytest.approx([0.44, 0.74])
    assert "MOCK DATA" not in html(app)
    assert calls[-1][1]["params"] == {"limit": 12, "offset": 0}


def test_form_sends_canonical_payload_and_renders_response(transport, prediction_fixture):
    routes, calls = transport
    routes[("POST", PREDICTIONS)] = (201, prediction_fixture)
    app = open_app("prediction")
    fill_prediction(app)
    button(app, "Buat estimasi").click().run()
    assert not app.exception
    posts = [call["json"] for (method, _), call in calls if method == "POST"]
    expected = read_example("prediction_request.json")
    expected["worker_count"] = 30.5
    assert posts == [expected]
    assert PredictionRequest.model_validate(posts[0]).worker_count == 30.5
    markup = html(app)
    for text in ("74.0%", "80.0%", "-6.0 pp", "Di bawah target",
                 prediction_fixture["prediction_id"], prediction_fixture["model_version"]):
        assert text in markup
    assert len(app.get("plotly_chart")) == 1


def test_prediction_draft_restores_across_pages_without_posting(transport):
    _, calls = transport
    app = open_app("prediction")
    fill_prediction(app)
    button(app, "Simpan draf sesi").click().run()
    assert any("Draf disimpan" in status.value for status in app.success)
    app.switch_page("pages/overview.py").run()
    app.switch_page("pages/prediction.py").run()
    assert not app.exception
    assert app.date_input(key="production_date").value == date(2026, 12, 1)
    assert app.selectbox(key="department").value == Department.SEWING
    assert app.number_input(key="team_id").value == 3
    assert app.number_input(key="target_percent").value == 80.0
    assert app.number_input(key="smv_minutes").value == 26.16
    assert app.number_input(key="worker_count").value == 30.5
    assert not any(method == "POST" for (method, _), _ in calls)


def test_invalid_form_does_not_call_prediction(transport):
    _, calls = transport
    app = open_app("prediction")
    fill_prediction(app)
    app.number_input(key="target_percent").set_value(0.0)
    button(app, "Buat estimasi").click().run()
    assert not app.exception
    assert any("Periksa isian formulir" in error.value for error in app.error)
    assert any("hingga 100%" in caption.value for caption in app.caption)
    assert not any(method == "POST" for (method, _), _ in calls)


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        (requests.Timeout(), "Waktu tunggu backend habis"),
        ((422, {"detail": [{"loc": ["body", "worker_count"]}]}), "HTTP 422"),
        ((503, {"detail": "model unavailable"}), "HTTP 503"),
        ((201, {"prediction_id": "invalid"}), "tidak sesuai"),
    ],
)
def test_prediction_api_failures_render_without_fallback(transport, reply, message):
    routes, _ = transport
    routes[("POST", PREDICTIONS)] = reply
    app = open_app("prediction")
    fill_prediction(app)
    button(app, "Buat estimasi").click().run()
    assert not app.exception
    assert any(message in error.value for error in app.error)
    assert not app.get("plotly_chart")
    if "HTTP 422" == message:
        assert any("Jumlah pekerja ekuivalen" in caption.value for caption in app.caption)


def test_offline_overview_clearly_reports_unavailable_data(transport):
    routes, _ = transport
    routes[("GET", "/health")] = requests.ConnectionError()
    routes[("GET", OVERVIEW)] = requests.ConnectionError()
    app = open_app()
    assert any("tidak dapat terhubung" in error.value for error in app.error)
    assert "—" in html(app)
    assert "MOCK DATA" not in html(app)


def test_explicit_mock_mode_is_labeled_and_makes_no_http_calls(transport, monkeypatch):
    _, calls = transport
    monkeypatch.setenv("PRODPULSE_FRONTEND_MODE", "mock")
    app = open_app()
    markup = html(app)
    assert "MOCK DATA" in markup
    assert markup.count('<div class="pp-kpi">') == 4
    trend, teams = [json.loads(chart.proto.spec) for chart in app.get("plotly_chart")]
    assert trend["data"][0]["type"] == "scatter"
    assert len(trend["data"][0]["x"]) == 12
    assert teams["data"][0]["type"] == "bar"
    assert len(teams["data"][0]["x"]) == 12
    assert teams["layout"]["plot_bgcolor"] == "#9BE198"
    assert calls == []


def test_empty_prediction_history(transport):
    routes, calls = transport
    routes[("GET", PREDICTIONS)] = (200, {"items": [], "total": 0, "limit": 20, "offset": 0})
    app = open_app("history")
    assert any("Belum ada prediksi tersimpan" in item.value for item in app.info)
    assert not app.dataframe
    assert calls[-1] == (("GET", PREDICTIONS), {
        "json": None, "params": {"limit": 20, "offset": 0}, "timeout": (2, 12),
        "allow_redirects": False,
    })


def test_server_pagination_and_detail(transport, prediction_fixture):
    routes, calls = transport
    second = {**prediction_fixture, "prediction_id": "other-prediction"}
    records = [prediction_fixture] * 20 + [second]

    def page_response(call):
        limit, offset = call["params"]["limit"], call["params"]["offset"]
        return 200, {"items": records[offset:offset + limit], "total": len(records),
                     "limit": limit, "offset": offset}

    routes[("GET", PREDICTIONS)] = page_response
    routes[("GET", f"{PREDICTIONS}/other-prediction")] = (200, second)
    app = open_app("history")
    assert button(app, "Sebelumnya").disabled
    table = app.dataframe[0].value
    assert table.loc[0, "Target"] == 80.0
    assert table.loc[0, "Estimasi"] == 74.0
    assert table.loc[0, "Selisih"] == -6.0
    button(app, "Berikutnya").click().run()
    assert not app.exception
    assert button(app, "Berikutnya").disabled
    assert any("21–21 dari 21" in caption.value for caption in app.caption)
    app.selectbox(key="history_selection").select(second["prediction_id"]).run()
    assert calls[-1][0] == ("GET", f"{PREDICTIONS}/other-prediction")
    assert "other-prediction" in html(app)
    button(app, "Sebelumnya").click().run()
    pages = [kwargs["params"] for key, kwargs in calls if key == ("GET", PREDICTIONS)]
    assert pages == [{"limit": 20, "offset": offset} for offset in (0, 20, 20, 0)]
    assert app.selectbox(key="history_selection").value is None


def test_history_department_filter_only_applies_to_the_loaded_page(transport, prediction_fixture):
    routes, calls = transport
    finishing = {**prediction_fixture, "department": "finishing", "prediction_id": "finishing-id"}
    routes[("GET", PREDICTIONS)] = (200, {
        "items": [prediction_fixture, finishing], "total": 2, "limit": 20, "offset": 0,
    })
    app = open_app("history")
    app.selectbox(key="history_department").select(Department.FINISHING).run()
    assert not app.exception
    assert app.dataframe[0].value["Departemen"].tolist() == ["Finishing"]
    assert app.selectbox(key="history_selection").options[0].endswith("finishing-id")
    params = [kwargs["params"] for key, kwargs in calls if key == ("GET", PREDICTIONS)]
    assert params == [{"limit": 20, "offset": 0}] * 2


def test_chat_preserves_server_conversation_and_clears_it(transport, prediction_fixture):
    routes, calls = transport
    result_id = prediction_fixture["prediction_id"]
    routes[("POST", PREDICTIONS)] = (201, prediction_fixture)
    routes[("POST", CHAT)] = (200, {
        "conversation_id": "from-server",
        "answer": "Respons asli dari fixture HTTP.",
        "status": "answered",
        "evidence": [{"type": "prediction", "id": result_id}],
    })

    app = open_app("prediction")
    fill_prediction(app)
    button(app, "Buat estimasi").click().run()
    button(app, "Bahas prediksi dengan AI Assistant").click().run()
    app.switch_page("pages/assistant.py").run()
    assert not app.exception
    assert result_id in html(app)
    app.chat_input[0].set_value("Jelaskan selisihnya.").run()
    app.chat_input[0].set_value("Apa artinya untuk tim?").run()
    assert not app.exception
    assert "Respons asli dari fixture HTTP." in html(app)
    assert f"Prediksi: {result_id}" in html(app)
    button(app, "Hapus percakapan ini").click().run()
    assert "Respons asli dari fixture HTTP." not in html(app)
    app.chat_input[0].set_value("Mulai lagi.").run()

    payloads = [kwargs["json"] for key, kwargs in calls if key == ("POST", CHAT)]
    assert [payload["conversation_id"] for payload in payloads] == [None, "from-server", None]
    assert [payload["prediction_id"] for payload in payloads] == [result_id] * 3


@pytest.mark.parametrize(
    "reply",
    [
        (200, {"conversation_id": "from-server", "answer": "Jangan tampilkan ini.", "status": "unavailable"}),
        (503, {"detail": "unavailable"}),
    ],
)
def test_chat_unavailable_never_renders_an_assistant_answer(transport, reply):
    routes, _ = transport
    routes[("POST", CHAT)] = reply
    app = open_app("assistant")
    app.chat_input[0].set_value("Apakah ada prediksi?").run()
    assert not app.exception
    assert len(app.get("chat_message")) == 1
    assert "Jangan tampilkan ini." not in html(app)
    assert any("tidak tersedia" in state.value for state in [*app.error, *app.warning])


def test_assistant_evidence_opens_prediction_outside_current_history_page(transport, prediction_fixture):
    routes, calls = transport
    result_id = prediction_fixture["prediction_id"]
    routes[("POST", CHAT)] = (200, {
        "conversation_id": "from-server", "answer": "Prediksi ditemukan.",
        "status": "answered", "evidence": [{"type": "prediction", "id": result_id}],
    })
    routes[("GET", PREDICTIONS)] = (200, {"items": [], "total": 0, "limit": 20, "offset": 0})
    routes[("GET", f"{PREDICTIONS}/{result_id}")] = (200, prediction_fixture)
    app = open_app("assistant")
    app.chat_input[0].set_value("Buka bukti prediksi.").run()
    button(app, "Buka detail bukti").click().run()
    app.switch_page("pages/history.py").run()
    assert not app.exception
    assert any(title.value == "Bukti dari AI Assistant" for title in app.header)
    assert result_id in html(app)
    assert any(key == ("GET", f"{PREDICTIONS}/{result_id}") for key, _ in calls)
    button(app, "Tutup detail sumber").click().run()
    assert result_id not in html(app)
    assert not app.exception


def test_prediction_id_is_encoded_in_detail_path(transport, prediction_fixture):
    routes, _ = transport
    prediction_id = "id/with space"
    routes[("GET", f"{PREDICTIONS}/id%2Fwith%20space")] = (
        200, {**prediction_fixture, "prediction_id": prediction_id},
    )
    assert ApiClient(BASE_URL).get_prediction(prediction_id).prediction_id == prediction_id


def test_detail_rejects_a_response_for_a_different_prediction(transport, prediction_fixture):
    routes, _ = transport
    routes[("GET", f"{PREDICTIONS}/requested-id")] = (200, prediction_fixture)
    with pytest.raises(ApiError, match="invalid_response"):
        ApiClient(BASE_URL).get_prediction("requested-id")


def test_invalid_response_is_reported_as_an_api_error(transport):
    routes, _ = transport
    routes[("GET", OVERVIEW)] = (200, [{"count": 1}])
    with pytest.raises(ApiError, match="invalid_response"):
        ApiClient(BASE_URL).get_overview()
