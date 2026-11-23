"""Translate API and validation failures into user-facing Streamlit states."""

from html import escape

import streamlit as st
from pydantic import ValidationError

from frontend.api_client import ApiError
from frontend.formatters import FIELD_LABELS

ERROR_MESSAGES = {
    "timeout": "Waktu tunggu backend habis.",
    "connection": "Frontend tidak dapat terhubung ke backend.",
    "transport": "Permintaan ke backend gagal dikirim.",
    "validation": "Backend menolak input (HTTP 422). Periksa isian yang ditandai.",
    "unavailable": "Layanan sedang tidak tersedia (HTTP 503).",
    "not_found": "Data atau layanan belum ditemukan (HTTP 404).",
    "http": "Backend mengembalikan kesalahan.",
    "invalid_response": "Respons backend tidak sesuai dengan kontrak yang diperlukan.",
}

FIELD_ERRORS = {
    "production_date": "Pilih tanggal produksi yang valid.",
    "department": "Pilih Sewing atau Finishing.",
    "team_id": "Masukkan ID tim berupa bilangan bulat minimal 1.",
    "target_productivity": "Masukkan target lebih dari 0% hingga 100%.",
    "smv_minutes": "Masukkan SMV yang lebih dari 0 menit.",
    "worker_count": "Masukkan jumlah pekerja lebih dari 0. Desimal diperbolehkan.",
}


def show_api_error(error: ApiError, purpose: str) -> None:
    message = ERROR_MESSAGES[error.kind]
    st.error(f"{purpose} {message}")
    fields = [FIELD_LABELS[field] for field in error.fields if field in FIELD_LABELS]
    if fields:
        st.caption("Periksa " + ", ".join(fields) + ".")


def show_validation_error(error: ValidationError) -> None:
    st.error("Periksa isian formulir sebelum membuat estimasi.")
    for field in dict.fromkeys(issue["loc"][0] for issue in error.errors()):
        st.caption(FIELD_ERRORS.get(field, "Periksa nilai yang dimasukkan."))


def health_summary(snapshot: dict | ApiError, *, is_mock: bool) -> None:
    st.html('<h2 class="pp-sidebar-heading">Status sistem</h2>')
    if isinstance(snapshot, ApiError):
        st.warning(ERROR_MESSAGES[snapshot.kind])
        return

    labels = (("Backend", "status"), ("Database", "db_status"), ("Model", "model_status"))
    rows = []
    for label, field in labels:
        value = snapshot.get(field)
        text = value if isinstance(value, str) and value.strip() else "Belum dilaporkan"
        rows.append(f"<div><dt>{label}</dt><dd>{escape(text)}</dd></div>")
    st.caption("Status fixture lokal." if is_mock else "Dilaporkan oleh endpoint kesehatan.")
    st.html(f'<dl class="pp-health">{"".join(rows)}</dl>')
