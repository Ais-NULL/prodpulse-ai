"""Server-paginated prediction history and detail selection."""

from hashlib import sha256

import streamlit as st

from frontend.api_client import ApiError
from frontend.components.prediction_result import show_prediction_result
from frontend.components.presentation import page_header, panel_heading
from frontend.components.states import show_api_error
from frontend.formatters import DEPARTMENT_LABELS, TARGET_LABELS, prediction_context
from frontend.routes import ASSISTANT_PAGE, PREDICTION_PAGE
from frontend.session import get_api
from shared.contracts import Department, PredictionListResponse, PredictionResponse

PAGE_LIMIT = 20


def set_offset(offset: int) -> None:
    st.session_state.history_offset = offset
    st.session_state.pop("history_selection", None)


def load_page(offset: int) -> PredictionListResponse:
    api = get_api()
    page = api.list_predictions(limit=PAGE_LIMIT, offset=offset)
    if offset > 0 and not page.items and offset >= page.total:
        set_offset(0)
        page = api.list_predictions(limit=PAGE_LIMIT, offset=0)
    return page


def show_records(records: list[PredictionResponse], *, table_key: str) -> str | None:
    rows = [
        {
            "Tanggal produksi": result.production_date,
            "Departemen": DEPARTMENT_LABELS[result.department],
            "ID tim": result.team_id,
            "Target": result.target_productivity * 100,
            "Estimasi": result.predicted_productivity * 100,
            "Selisih": result.gap_percentage_points,
            "Status target": TARGET_LABELS[result.target_status],
            "Versi model": result.model_version,
        }
        for result in records
    ]
    # Streamlit reports positions. Reset the selection if the row identities change.
    row_ids = tuple(result.prediction_id for result in records)
    identity = sha256(repr(row_ids).encode("utf-8")).hexdigest()[:16]
    table = st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        key=f'{table_key}_{identity}',
        on_select=clear_selection,
        selection_mode="single-row",
        column_config={
            "Tanggal produksi": st.column_config.DateColumn("TANGGAL PRODUKSI", format="DD/MM/YYYY"),
            "Departemen": "DEPARTEMEN",
            "ID tim": "ID TIM",
            "Target": st.column_config.NumberColumn("TARGET", format="%.1f%%"),
            "Estimasi": st.column_config.NumberColumn("ESTIMASI", format="%.1f%%"),
            "Selisih": st.column_config.NumberColumn("SELISIH", format="%.1f pp"),
            "Status target": "STATUS TARGET",
            "Versi model": "VERSI MODEL",
        },
    )
    selected_rows = table.selection.rows
    if selected_rows and 0 <= selected_rows[0] < len(row_ids):
        return row_ids[selected_rows[0]]
    return None


def show_pagination(page: PredictionListResponse) -> None:
    previous, following = st.columns(2)
    previous.button(
        "Sebelumnya", disabled=page.offset <= 0, on_click=set_offset,
        args=(max(0, page.offset - page.limit),), width="stretch",
    )
    next_offset = page.offset + page.limit
    following.button(
        "Berikutnya", disabled=next_offset >= page.total, on_click=set_offset,
        args=(next_offset,), width="stretch",
    )


def clear_selection() -> None:
    st.session_state.pop("history_selection", None)


def show_detail(records: list[PredictionResponse], row_id: str | None) -> None:
    st.header("Detail prediksi", anchor=False)
    options = {
        result.prediction_id: f"{prediction_context(result)} | {result.prediction_id}"
        for result in records
    }
    selected_id = st.selectbox(
        "Prediksi pada halaman ini", list(options), index=None,
        placeholder="Pilih prediksi", format_func=options.__getitem__, key="history_selection",
    )
    selected_id = selected_id or row_id
    if selected_id is None:
        st.info("Pilih baris atau gunakan daftar prediksi untuk membuka detail.")
        return
    show_prediction_by_id(selected_id)


def show_prediction_by_id(prediction_id: str) -> None:
    with st.spinner("Memuat detail prediksi…"):
        try:
            result = get_api().get_prediction(prediction_id)
        except ApiError as error:
            show_api_error(error, "Detail prediksi belum dapat dimuat.")
        else:
            show_prediction_result(result)


def render_history() -> None:
    page_header(
        "Riwayat prediksi",
        "Tinjau estimasi yang tersimpan dan buka kembali perbandingannya dengan target.",
    )
    source_id = st.session_state.get("history_source_id")
    if source_id is not None:
        st.header("Bukti dari AI Assistant", anchor=False)
        st.page_link(ASSISTANT_PAGE, label="Kembali ke AI Assistant", icon=":material/forum:")
        st.button(
            "Tutup detail sumber", on_click=st.session_state.pop, args=("history_source_id", None)
        )
        show_prediction_by_id(source_id)

    with st.container(key="pp_history_list"):
        panel_heading("Prediksi tersimpan")
        show_history_list(show_details=source_id is None)


def show_history_list(*, show_details: bool) -> None:
    with st.spinner("Memuat riwayat prediksi…"):
        try:
            page = load_page(st.session_state.get("history_offset", 0))
        except ApiError as error:
            show_api_error(error, "Riwayat belum dapat dimuat.")
            st.button("Muat ulang riwayat")
            return

    if page.total == 0:
        st.info("Belum ada prediksi tersimpan.")
        st.page_link(PREDICTION_PAGE, label="Buat prediksi pertama", icon=":material/add_chart:")
        return

    records = page.items
    row_id = None
    if page.items:
        department = st.selectbox(
            "Departemen pada halaman ini",
            ["all", *Department],
            format_func=lambda item: "Semua departemen" if item == "all" else DEPARTMENT_LABELS[item],
            key="history_department",
            on_change=clear_selection,
        )
        records = [result for result in page.items if department == 'all' or result.department == department]
        st.caption(f"Menampilkan {page.offset + 1}–{page.offset + len(page.items)} dari {page.total} prediksi.")
        if records:
            row_id = show_records(records, table_key=f"history_table_{page.offset}_{department}")
        else:
            st.info("Departemen ini tidak memiliki prediksi pada halaman yang sedang dibuka.")
    else:
        st.info("Halaman ini belum memuat prediksi. Muat ulang riwayat untuk melihat perubahan.")
        st.button("Muat ulang riwayat")

    show_pagination(page)
    if records and show_details:
        show_detail(records, row_id)


render_history()
