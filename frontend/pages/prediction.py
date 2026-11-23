"""Pre-shift form and the most recent result in this session."""

from datetime import date

import streamlit as st
from pydantic import ValidationError

from frontend.api_client import ApiError
from frontend.components.prediction_result import show_prediction_result
from frontend.components.presentation import page_header, panel_heading
from frontend.components.states import show_api_error, show_validation_error
from frontend.formatters import DEPARTMENT_LABELS, FIELD_LABELS
from frontend.routes import HISTORY_PAGE
from frontend.session import get_api
from shared.contracts import Department, PredictionRequest

page_header(
    "Prediksi baru",
    "Masukkan rencana sebelum shift untuk memperkirakan produktivitas satu tim.",
)

draft = st.session_state.get("prediction_draft", {})
departments = list(Department)
previous_department = draft.get("department")
department_index = departments.index(previous_department) if previous_department is not None else None

with st.container(key="pp_prediction_form"), st.form(
    "prediction_form", clear_on_submit=False, enter_to_submit=False, border=False
):
    panel_heading("Rencana produksi")
    left, right = st.columns(2)
    with left:
        production_date = st.date_input(
            FIELD_LABELS["production_date"], value=draft.get("production_date", date.today()),
            format="DD/MM/YYYY",
            key="production_date",
        )
        department = st.selectbox(
            FIELD_LABELS["department"], departments, index=department_index,
            format_func=DEPARTMENT_LABELS.__getitem__, placeholder="Pilih departemen", key="department",
        )
        team_id = st.number_input(
            FIELD_LABELS["team_id"], min_value=1, value=draft.get("team_id"), step=1,
            placeholder="Contoh: 3",
            key="team_id",
        )
    with right:
        target_percent = st.number_input(
            FIELD_LABELS["target_productivity"], value=draft.get("target_percent"), min_value=0.0, max_value=100.0,
            step=1.0, format="%g", placeholder="Contoh: 80", key="target_percent",
        )
        smv_minutes = st.number_input(
            FIELD_LABELS["smv_minutes"], value=draft.get("smv_minutes"), min_value=0.0,
            step=0.01, format="%g", placeholder="Contoh: 26.16", key="smv_minutes",
        )
        worker_count = st.number_input(
            FIELD_LABELS["worker_count"], value=draft.get("worker_count"), min_value=0.0,
            step=0.1, format="%g", placeholder="Contoh: 30.5", key="worker_count",
            help="Masukkan jumlah pekerja ekuivalen. Nilai desimal diperbolehkan.",
        )
    estimate, draft_action = st.columns(2)
    with estimate:
        submitted = st.form_submit_button("Buat estimasi", type="primary", width="stretch")
    with draft_action:
        save_draft = st.form_submit_button("Simpan draf sesi", width="stretch")

if submitted or save_draft:
    st.session_state.prediction_draft = {
        "production_date": production_date,
        "department": department,
        "team_id": team_id,
        "target_percent": target_percent,
        "smv_minutes": smv_minutes,
        "worker_count": worker_count,
    }
if save_draft:
    st.success("Draf disimpan untuk sesi ini.")
elif draft and not submitted:
    st.caption("Form memuat draf dari sesi ini.")

if submitted:
    st.session_state.pop("prediction_result", None)
    try:
        request = PredictionRequest(
            production_date=production_date,
            department=department,
            team_id=team_id,
            target_productivity=target_percent / 100 if target_percent is not None else None,
            smv_minutes=smv_minutes,
            worker_count=worker_count,
        )
    except ValidationError as error:
        show_validation_error(error)
    else:
        with st.spinner("Meminta estimasi dari backend…"):
            try:
                st.session_state.prediction_result = get_api().create_prediction(request)
            except ApiError as error:
                show_api_error(error, "Estimasi belum dapat ditampilkan.")
                if error.kind in {"timeout", "invalid_response", "transport", "http"}:
                    st.page_link(HISTORY_PAGE, label="Periksa riwayat sebelum mengirim ulang")

result = st.session_state.get("prediction_result")
if result is not None:
    show_prediction_result(result)
elif not submitted:
    st.info("Isi rencana produksi untuk melihat estimasi dan perbandingan target di sini.")
