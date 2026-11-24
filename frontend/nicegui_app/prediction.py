"""Plan one shift and display the result returned by the prediction API."""

from datetime import date
from html import escape

from nicegui import run, ui
from pydantic import ValidationError

from frontend.api_client import ApiError
from frontend.formatters import DEPARTMENT_LABELS, FIELD_LABELS, TARGET_LABELS, format_gap, format_ratio, prediction_context
from frontend.nicegui_app.shell import (
    ASSISTANT, HISTORY, PREDICTION, action_link, api_error, loading, notice, prediction_url,
    section_title, session, shell,
)
from shared.contracts import Department, PredictionRequest, PredictionResponse, TargetStatus

FIELD_ERRORS = {
    "production_date": "Pilih tanggal produksi yang valid.",
    "department": "Pilih departemen.",
    "team_id": "Masukkan nomor tim berupa bilangan bulat minimal 1.",
    "target_productivity": "Masukkan target lebih dari 0% hingga 100%.",
    "smv_minutes": "Masukkan SMV yang lebih dari 0 menit.",
    "worker_count": "Masukkan jumlah pekerja lebih dari 0. Desimal diperbolehkan.",
}


def result_panel(result: PredictionResponse):
    below = result.target_status == TargetStatus.BELOW_TARGET
    with ui.element("section").classes("panel result-panel"):
        with ui.row().classes("panel-head"):
            section_title("Perbandingan dengan target", prediction_context(result))
            ui.label(TARGET_LABELS[result.target_status]).classes("target-status below" if below else "target-status")
        with ui.element("dl").classes("result-metrics"):
            for label, value in (
                ("Estimasi tim", format_ratio(result.predicted_productivity)),
                ("Target", format_ratio(result.target_productivity)),
                ("Selisih", format_gap(result.gap_percentage_points)),
            ):
                with ui.element("div"):
                    ui.html(label, tag="dt")
                    ui.html(value, tag="dd")
        scale = max(1.0, result.predicted_productivity)
        with ui.element("div").classes("comparison"):
            for label, ratio, color in (
                ("Estimasi tim", result.predicted_productivity, "primary"),
                ("Target", result.target_productivity, "teal-8"),
            ):
                with ui.row().classes("comparison-row"):
                    ui.label(label)
                    ui.linear_progress(value=ratio / scale, show_value=False, color=color).props(
                        f'aria-label="{label}" aria-valuetext="{format_ratio(ratio)}"'
                    ).classes("comparison-bar")
        ui.label("Estimasi model untuk prototipe akademik.").classes("support")
        with ui.expansion("Detail rekaman", icon="info_outline").classes("data-expansion"):
            with ui.element("dl").classes("record-meta"):
                for label, value in (
                    ("ID prediksi", result.prediction_id),
                    ("Versi model", result.model_version),
                    ("Waktu tersimpan", result.created_at.isoformat(timespec="seconds")),
                ):
                    with ui.element("div"):
                        ui.html(label, tag="dt")
                        ui.html(escape(value), tag="dd")
        action_link("Bahas dengan AI Assistant", prediction_url(ASSISTANT, result.prediction_id), "chat_bubble_outline")


async def prediction_page():
    await ui.context.client.connected()
    state = session()
    workspace = shell(PREDICTION, "Prediksi baru", "Perkirakan produktivitas satu tim sebelum shift.",
                      is_mock=state.api.is_mock)
    fields = {}
    draft = state.draft
    with workspace, ui.element("div").classes("work-grid"):
        with ui.element("section").classes("panel workflow-panel"):
            section_title("Rencana produksi", "Lengkapi tanggal, tim, dan parameter produksi.")
            with ui.element("div").classes("form-grid"):
                fields["production_date"] = ui.input(
                    FIELD_LABELS["production_date"], value=draft.get("production_date", date.today().isoformat())
                ).props("type=date outlined stack-label")
                with ui.element("fieldset").classes("department-field"):
                    ui.html(FIELD_LABELS["department"], tag="legend")
                    fields["department"] = ui.radio(
                        {department.value: DEPARTMENT_LABELS[department] for department in Department},
                        value=draft.get("department"),
                    ).props("inline")
                for name, step, hint in (
                    ("team_id", 1, "Contoh 3"),
                    ("target_productivity", None, "Contoh 80"),
                    ("smv_minutes", None, "Contoh 26.16"),
                    ("worker_count", None, "Contoh 30.5"),
                ):
                    fields[name] = ui.number(FIELD_LABELS[name], value=draft.get(name), step=step, placeholder=hint).props(
                        "outlined inputmode=" + ("numeric" if name == "team_id" else "decimal")
                    )
                for widget in fields.values():
                    widget.classes("form-field")
            feedback = ui.element("div").classes("feedback-slot")
            with ui.row().classes("form-actions"):
                submit = ui.button("Buat estimasi", icon="insights").props("no-caps unelevated").classes("main-button")
                save = ui.button("Simpan draf sesi", icon="bookmark_border").props("no-caps outline")
        result = ui.element("div").classes("result-slot").props('aria-live="polite"')

    def values():
        return {name: widget.value for name, widget in fields.items()}

    def save_draft():
        state.draft = values()
        feedback.clear()
        with feedback:
            notice("Draf disimpan untuk sesi ini.", tone="success")

    async def submit_prediction():
        if state.submitting:
            return
        feedback.clear()
        state.draft = values()
        data = state.draft.copy()
        if data["target_productivity"] is not None:
            data["target_productivity"] /= 100
        try:
            request = PredictionRequest.model_validate(data)
        except ValidationError as error:
            with feedback:
                notice("Periksa isian sebelum membuat estimasi.", tone="error")
                with ui.element("ul").classes("validation-list"):
                    for field in dict.fromkeys(issue["loc"][0] for issue in error.errors()):
                        ui.html(FIELD_ERRORS[field], tag="li")
            return
        state.submitting = True
        submit.disable()
        try:
            with feedback:
                loading("Meminta estimasi…")
            response = await run.io_bound(state.api.create_prediction, request)
        except ApiError as error:
            feedback.clear()
            with feedback:
                api_error("Estimasi belum dapat ditampilkan.", error)
                if error.kind in {"timeout", "invalid_response", "transport", "http"}:
                    action_link("Periksa riwayat sebelum mengirim ulang", HISTORY, "history")
        else:
            state.result_id = response.prediction_id
            feedback.clear()
            with feedback:
                notice("Estimasi tersimpan.", tone="success")
            result.clear()
            with result:
                result_panel(response)
            ui.run_javascript(
                "if (matchMedia('(max-width: 740px)').matches) "
                "document.querySelector('.result-slot').scrollIntoView({block:'start'});"
            )
        finally:
            state.submitting = False
            submit.enable()

    submit.on_click(submit_prediction)
    save.on_click(save_draft)
    if draft:
        with feedback:
            notice("Form memuat draf sesi ini.")
    if state.result_id is None:
        with result, ui.element("section").classes("panel empty-panel"):
            ui.icon("assessment", size="29px").classes("empty-icon")
            section_title("Estimasi akan muncul di sini", "Setelah dibuat, hasil dapat dibandingkan dengan target produksi.")
    else:
        with result:
            loading("Memuat estimasi sesi ini…")
        try:
            response = await run.io_bound(state.api.get_prediction, state.result_id)
        except ApiError as error:
            result.clear()
            with result:
                api_error("Estimasi terakhir belum dapat dimuat.", error)
        else:
            result.clear()
            with result:
                result_panel(response)
