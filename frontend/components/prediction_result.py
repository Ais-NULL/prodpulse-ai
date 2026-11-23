"""Presentation of a stored prediction in the new prediction and history pages."""

import streamlit as st

from frontend.components.charts import show_comparison
from frontend.components.presentation import metrics, panel_heading, plain_text
from frontend.formatters import TARGET_LABELS, format_gap, format_ratio, prediction_context
from frontend.session import discuss_prediction
from shared.contracts import PredictionResponse


def show_prediction_result(result: PredictionResponse) -> None:
    with st.container(key="pp_prediction_result"):
        panel_heading("Perbandingan dengan target")
        st.caption(prediction_context(result))
        metrics(
            ("Estimasi model", format_ratio(result.predicted_productivity), "Produktivitas tim pra-shift"),
            ("Target produksi", format_ratio(result.target_productivity), "Target yang dimasukkan"),
            ("Selisih", format_gap(result.gap_percentage_points), TARGET_LABELS[result.target_status]),
        )
        show_comparison(result)
        st.caption("Estimasi untuk prototipe akademik.")
        st.markdown("**Detail prediksi**")
        plain_text(
            f"ID prediksi: {result.prediction_id}\n"
            f"Versi model: {result.model_version}\n"
            f"Waktu tersimpan: {result.created_at.isoformat(timespec='seconds')}"
        )
        if st.button("Bahas prediksi dengan AI Assistant", width="stretch"):
            discuss_prediction(result)
