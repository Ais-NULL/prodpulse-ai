"""Manufacturing overview, with demo analytics gated to mock mode."""

from collections import defaultdict
from statistics import mean

import streamlit as st

from frontend.api_client import ApiError
from frontend.components.charts import show_team_chart, show_trend_chart
from frontend.components.dashboard import dashboard_metrics, status_tiles
from frontend.components.presentation import page_header, panel_heading
from frontend.components.states import show_api_error
from frontend.formatters import DEPARTMENT_LABELS, format_count, format_ratio
from frontend.mock_analytics import historical_trend, team_productivity
from frontend.routes import PREDICTION_PAGE
from frontend.session import get_api, get_health, invalidate_health
from shared.contracts import PredictionResponse


def summarize_estimates(
    records: list[PredictionResponse],
) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
    by_date = defaultdict(list)
    by_team = defaultdict(list)
    for record in records:
        by_date[record.production_date.isoformat()].append(record.predicted_productivity)
        team_label = f"{DEPARTMENT_LABELS[record.department]} {record.team_id}"
        by_team[team_label].append(record.predicted_productivity)
    return (
        [(label, mean(values)) for label, values in sorted(by_date.items())],
        [(label, mean(values)) for label, values in sorted(by_team.items())],
    )

page_header("Overview", "", overview=True)
api = get_api()

overview = None
model_version = None
with st.spinner("Memuat ringkasan produktivitas…"):
    try:
        overview = api.get_overview()
    except ApiError as error:
        show_api_error(error, "Ringkasan belum dapat dimuat.")
    if overview is not None:
        try:
            model_version = api.get_model_version()
        except ApiError:
            pass

dataset_note = "Catatan simulasi · 2025" if api.is_mock else "Catatan produksi historis"
prediction_note = "Prediksi simulasi" if api.is_mock else "Estimasi pra-shift tersimpan"
dashboard_metrics(
    ("Historical records", format_count(overview.historical_records if overview else None),
     dataset_note, "history"),
    ("Predictions generated", format_count(overview.prediction_count if overview else None),
     prediction_note, "predictions"),
    ("Avg. productivity", format_ratio(overview.mean_historical_productivity if overview else None),
     "Rata-rata simulasi 2025" if api.is_mock else "Rata-rata aktual historis", "productivity"),
    ("Active model", model_version or "—",
     "Model contoh" if api.is_mock else ("Versi model API" if model_version else "Versi belum tersedia"),
     "model"),
)

trend_points, team_points = [], []
sample_size = 0
charts_unavailable = overview is None
if api.is_mock:
    trend_points, team_points = historical_trend(), team_productivity()
elif overview is not None and overview.prediction_count > 0:
    with st.spinner("Memuat prediksi untuk ringkasan…"):
        try:
            predictions = api.list_predictions(limit=12, offset=0).items
        except ApiError as error:
            charts_unavailable = True
            show_api_error(error, "Grafik estimasi belum dapat dimuat.")
        else:
            sample_size = len(predictions)
            trend_points, team_points = summarize_estimates(predictions)

source = "Simulasi historis 2025" if api.is_mock else "Estimasi dari prediksi tersimpan"

with st.container(key="pp_overview_mid"):
    status, trend = st.columns([1, 3.14], gap="small")
    with status:
        status_tiles(get_health())
    with trend, st.container(key="pp_trend_panel"):
        trend_title = "Tren produktivitas historis" if api.is_mock else "Rata-rata estimasi per tanggal"
        st.html(f'<h2 class="pp-trend-title">{trend_title}</h2>')
        show_trend_chart(trend_points, source=source, unavailable=charts_unavailable)

with st.container(key="pp_overview_bottom"):
    action, teams = st.columns([1, 3.14], gap="small")
    with action, st.container(key="pp_quick_action"):
        if st.button("New Prediction", icon=":material/south:", width="stretch"):
            st.switch_page(PREDICTION_PAGE)
    with teams, st.container(key="pp_team_panel"):
        panel_heading("Produktivitas historis per tim" if api.is_mock else "Rata-rata estimasi per tim")
        show_team_chart(team_points, source=source, unavailable=charts_unavailable)

if sample_size:
    st.caption(f"Grafik diringkas dari {sample_size} prediksi pada halaman pertama riwayat.")

if overview is None:
    st.button("Muat ulang ringkasan", on_click=invalidate_health)
elif overview.historical_records == 0:
    st.caption("Belum ada catatan historis dari API.")
