"""Browse server-paginated predictions and open their details."""

from html import escape

from nicegui import run, ui

from frontend.api_client import ApiError
from frontend.formatters import DEPARTMENT_LABELS, TARGET_LABELS, format_gap, format_ratio
from frontend.nicegui_app.prediction import result_panel
from frontend.nicegui_app.shell import HISTORY, PREDICTION, action_link, api_error, loading, notice, section_title, session, shell
from shared.contracts import Department, PredictionResponse, TargetStatus

PAGE_LIMIT = 20


def record_row(record: PredictionResponse, open_detail):
    below = record.target_status == TargetStatus.BELOW_TARGET
    with ui.element("li").classes("history-item"):
        with ui.row().classes("history-team"):
            ui.icon("groups", size="20px").classes("metric-icon blue")
            with ui.column().classes("section-title"):
                ui.label(f"{DEPARTMENT_LABELS[record.department]} · Tim {record.team_id:02}").classes("record-name")
                ui.label(f"{record.production_date:%d/%m/%Y} · {record.model_version}").classes("support")
        with ui.element("dl").classes("history-values"):
            for label, value in (
                ("Estimasi", format_ratio(record.predicted_productivity)),
                ("Target", format_ratio(record.target_productivity)),
                ("Selisih", format_gap(record.gap_percentage_points)),
            ):
                with ui.element("div"):
                    ui.html(label, tag="dt")
                    ui.html(escape(value), tag="dd")
        ui.label(TARGET_LABELS[record.target_status]).classes("target-status below" if below else "target-status")

        async def view():
            await open_detail(record.prediction_id)

        ui.button("Lihat detail", icon="arrow_forward", on_click=view).props(
            f'flat no-caps aria-label="Lihat detail Tim {record.team_id:02}, {record.production_date:%d/%m/%Y}"'
        ).classes("row-action")


async def history_page(prediction_id: str | None = None):
    await ui.context.client.connected()
    api = session().api
    workspace = shell(HISTORY, "Riwayat prediksi", "Temukan estimasi tersimpan dan bandingkan dengan target tim.",
                      is_mock=api.is_mock)
    with workspace:
        detail = ui.element("div").classes("detail-slot")
        with ui.element("section").classes("panel workflow-panel"):
            with ui.row().classes("panel-head"):
                section_title("Prediksi tersimpan", "Pilih rekaman untuk melihat detail.")
                action_link("Buat prediksi", PREDICTION, "add", primary=True)
            list_area = ui.element("div").classes("section-stack")

    detail_request = 0

    def close_detail():
        nonlocal detail_request
        detail_request += 1
        detail.clear()

    async def open_detail(record_id):
        nonlocal detail_request
        close_detail()
        active_request = detail_request
        with detail:
            loading("Memuat detail prediksi…")
        ui.run_javascript("document.querySelector('.detail-slot').scrollIntoView({block:'start'})")
        try:
            record = await run.io_bound(api.get_prediction, record_id)
        except ApiError as error:
            if active_request == detail_request:
                detail.clear()
                with detail:
                    api_error("Detail prediksi belum dapat dimuat.", error)
        else:
            if active_request == detail_request:
                detail.clear()
                with detail:
                    result_panel(record)
        if active_request == detail_request:
            with detail:
                ui.button("Tutup detail", icon="close", on_click=close_detail).props("flat no-caps")

    department = "all"

    async def load_page(offset):
        list_area.clear()
        with list_area:
            loading("Memuat prediksi tersimpan…")
        try:
            page = await run.io_bound(api.list_predictions, limit=PAGE_LIMIT, offset=offset)
            if offset and not page.items and offset >= page.total:
                page = await run.io_bound(api.list_predictions, limit=PAGE_LIMIT, offset=0)
        except ApiError as error:
            list_area.clear()
            with list_area:
                api_error("Riwayat belum dapat dimuat.", error)

                async def retry():
                    await load_page(offset)

                ui.button("Muat ulang riwayat", on_click=retry).props("outline no-caps")
            return
        list_area.clear()
        with list_area:
            if page.total == 0:
                notice("Belum ada prediksi tersimpan.", "Hasil estimasi yang tersimpan akan tampil di sini.")
                return
            with ui.row().classes("history-toolbar"):
                with ui.column().classes("section-title"):
                    ui.label("Departemen pada halaman ini").classes("support")
                    filter_box = ui.toggle(
                        {"all": "Semua", **{d.value: DEPARTMENT_LABELS[d] for d in Department}},
                        value=department,
                    ).props('no-caps unelevated aria-label="Departemen pada halaman ini"').classes("period-control")
                ui.label(f"{page.offset + 1}–{page.offset + len(page.items)} dari {page.total} prediksi"
                         if page.items else "Halaman belum memuat prediksi.").classes("support")
            records_area = ui.element("div")

            def render_records(value):
                nonlocal department
                department = value
                records_area.clear()
                records = [item for item in page.items if value == "all" or item.department.value == value]
                with records_area:
                    if not records:
                        notice("Halaman ini belum memuat prediksi untuk filter tersebut.")
                        return
                    with ui.element("ul").classes("history-records"):
                        for record in records:
                            record_row(record, open_detail)

            filter_box.on_value_change(lambda event: render_records(event.value))
            render_records(department)

            async def previous():
                await load_page(max(0, page.offset - page.limit))

            async def following():
                await load_page(page.offset + page.limit)

            with ui.row().classes("pagination"):
                ui.button("Sebelumnya", icon="chevron_left", on_click=previous).props(
                    "outline no-caps"
                ).set_enabled(page.offset > 0)
                ui.button("Berikutnya", icon="chevron_right", on_click=following).props(
                    "outline no-caps"
                ).set_enabled(page.offset + page.limit < page.total)

    await load_page(0)
    if prediction_id:
        await open_detail(prediction_id)
