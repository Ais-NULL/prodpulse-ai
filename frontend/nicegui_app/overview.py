"""Overview dashboard for historical data and saved estimates."""

import asyncio
from collections import defaultdict
from html import escape
from statistics import mean

import plotly.graph_objects as go
from nicegui import run, ui

from frontend.api_client import ApiError
from frontend.formatters import DEPARTMENT_LABELS, format_count, format_gap, format_ratio
from frontend.mock_analytics import MONTH_LABELS, SAMPLE_ROWS
from frontend.nicegui_app.shell import (
    HISTORY, OVERVIEW, PREDICTION, action_link, api_error, loading, notice,
    prediction_url, section_title, session, shell,
)
from shared.contracts import TargetStatus

PERIODS = {3: "3 bulan", 6: "6 bulan", 12: "12 bulan"}

def metric(icon, label, value, note, color):
    with ui.element("article").classes("metric"):
        with ui.row().classes("metric-top"):
            ui.icon(icon, size="19px").classes(f"metric-icon {color}")
            ui.label(label)
        ui.label(value).classes("metric-value")
        ui.label(note).classes("support")


def trend_chart(points):
    months, values = zip(*points)
    fig = go.Figure(go.Scatter(
        x=months,
        y=values,
        mode="lines+markers",
        fill="tozeroy",
        fillcolor="rgba(65, 87, 225, .09)",
        line=dict(color="#4157e1", width=3),
        marker=dict(color="#4157e1", size=7, line=dict(width=1.5, color="white")),
        hovertemplate="%{x} · %{y:.1%}<extra></extra>",
    ))
    fig.update_layout(
        autosize=True, height=248, margin=dict(l=47, r=12, t=14, b=34),
        template="none", plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="DM Sans, system-ui, sans-serif", size=12, color="#525e76"),
        dragmode=False,
        xaxis=dict(
            type="category", range=[-.28, len(months) - .72],
            fixedrange=True, showgrid=False, automargin=True,
        ),
        yaxis=dict(
            tickformat=".0%", fixedrange=True, gridcolor="#e8ebf4", zeroline=False,
            range=[0, max(1.0, max(values) + .05)], dtick=.25,
        ),
    )
    chart = fig.to_dict()
    chart["config"] = {"displayModeBar": False}
    ui.plotly(chart).classes("trend-chart annual-trend" if len(points) == 12 else "trend-chart")


def ranked_teams(teams):
    with ui.element("ol").classes("ranked-teams"):
        for index, (team, value) in enumerate(teams, start=1):
            with ui.element("li").classes("ranked-item"):
                ui.label(f"{index:02}").classes("rank-number")
                ui.label(f"Tim {team:02}").classes("rank-name")
                # The maximum follows the data so historical values over 100% fit.
                ui.linear_progress(value=value / max(1, teams[0][1]), show_value=False).props(
                    f'aria-label="Produktivitas Tim {team:02}" aria-valuetext="{format_ratio(value)}"'
                ).classes("rank-progress")
                ui.label(format_ratio(value)).classes("rank-value")


def historical_overview(month_count, prediction_count):
    first_month = 13 - month_count
    rows = [(day, team, value) for day, team, value in SAMPLE_ROWS if day.month >= first_month]
    by_month = defaultdict(list)
    by_team = defaultdict(list)
    for day, team, value in rows:
        by_month[day.month].append(value)
        by_team[team].append(value)
    period = f"{MONTH_LABELS[first_month - 1]}–Des 2025"
    trend = [(MONTH_LABELS[month - 1], mean(values)) for month, values in by_month.items()]
    teams = sorted(((team, mean(values)) for team, values in by_team.items()), key=lambda item: -item[1])

    with ui.element("section").classes("metrics").props('aria-label="Indikator produksi" aria-live="polite"'):
        metric("show_chart", "Produktivitas historis", format_ratio(mean(row[2] for row in rows)),
               f"Rata-rata aktual simulasi · {period}", "blue")
        metric("dataset", "Catatan produksi", format_count(len(rows)), f"Data historis · {period}", "aqua")
        metric("groups", "Tim tercatat", format_count(len(teams)), f"Data historis · {period}", "purple")
        metric("fact_check", "Prediksi tersimpan", format_count(prediction_count),
               "Semua prediksi simulasi", "amber")

    with ui.element("section").classes("analytics").props('aria-label="Analitik historis"'):
        with ui.element("article").classes("panel trend-panel"):
            section_title("Tren produktivitas", f"Rata-rata data historis simulasi per bulan · {period}")
            trend_chart(trend)
            with ui.expansion("Lihat angka per bulan", icon="table_chart").classes("data-expansion"):
                with ui.element("dl").classes("trend-data"):
                    for month, value in trend:
                        ui.html(escape(month), tag="dt")
                        ui.html(format_ratio(value), tag="dd")
        with ui.element("article").classes("panel teams-panel"):
            section_title("Produktivitas per tim", f"Rata-rata data historis simulasi · {period}")
            with ui.column().classes("ranking"):
                ranked_teams(teams[:5])
                with ui.dialog() as ranking_dialog, ui.card().classes("ranking-dialog"):
                    section_title("Peringkat seluruh tim", period)
                    ranked_teams(teams)
                    ui.button("Tutup", on_click=ranking_dialog.close).props("flat no-caps").classes("dialog-close")
                ui.button(f"Lihat semua {len(teams)} tim", on_click=ranking_dialog.open).props(
                    "flat no-caps"
                ).classes("text-button")


def prediction_snapshot(record):
    below_target = record.target_status == TargetStatus.BELOW_TARGET
    with ui.element("section").classes("panel prediction-panel"):
        with ui.row().classes("prediction-top"):
            section_title("Prediksi terakhir", f"Estimasi pra-shift · Model {record.model_version}")
            action_link("Buka detail", prediction_url(HISTORY, record.prediction_id), "arrow_forward")
        with ui.element("dl").classes("prediction-details"):
            for label, value in (
                ("Tim", f"{DEPARTMENT_LABELS[record.department]} · Tim {record.team_id:02}"),
                ("Tanggal produksi", f"{record.production_date:%d/%m/%Y}"),
                ("Estimasi", format_ratio(record.predicted_productivity)),
                ("Target", format_ratio(record.target_productivity)),
                ("Selisih", format_gap(record.gap_percentage_points)),
            ):
                with ui.element("div"):
                    ui.html(escape(label), tag="dt")
                    ui.html(escape(value), tag="dd")
            with ui.element("div"):
                ui.html("Status", tag="dt")
                ui.html("Di bawah target" if below_target else "Target tercapai", tag="dd").classes(
                    "target-status below" if below_target else "target-status"
                )


async def overview_page():
    await ui.context.client.connected()
    api = session().api
    workspace = shell(
        OVERVIEW, "Ringkasan produksi",
        "Pantau produktivitas historis dan cek estimasi tim sebelum shift.", is_mock=api.is_mock,
    )
    with workspace:
        with ui.element("section").classes("shift-banner"):
            with ui.column().classes("banner-content"):
                ui.html("Rencanakan shift berikutnya", tag="h2")
                ui.label("Masukkan rencana produksi untuk memperkirakan produktivitas tim.")
                with ui.link(target=PREDICTION).classes("shift-action"):
                    ui.icon("add", size="19px")
                    ui.label("Buat prediksi")
                    ui.icon("arrow_forward", size="15px")

        if api.is_mock:
            count = api.get_overview().prediction_count
            historical = ui.refreshable(historical_overview)
            with ui.row().classes("filter-row"):
                section_title("Kinerja produksi", "Periode berlaku untuk data historis.")
                ui.toggle(PERIODS, value=12, on_change=lambda event: historical.refresh(
                    event.value, count
                )).props('no-caps unelevated aria-label="Periode historis"').classes("period-control")
            historical(12, count)
            records = api.list_predictions(limit=1, offset=0).items
            if records:
                prediction_snapshot(records[0])
        else:
            await render_api_overview(api)


async def render_api_overview(api):
    content = ui.element("div").classes("section-stack")

    async def fetch(method, **kwargs):
        try:
            return await run.io_bound(method, **kwargs)
        except ApiError as error:
            return error

    async def refresh():
        content.clear()
        with content:
            loading("Memuat laporan dari backend…")
        summary, health, model, predictions = await asyncio.gather(
            fetch(api.get_overview), fetch(api.get_health), fetch(api.get_model_version),
            fetch(api.list_predictions, limit=12, offset=0),
        )
        content.clear()
        with content:
            if isinstance(summary, ApiError):
                api_error("Ringkasan belum dapat dimuat.", summary)
                ui.button("Muat ulang", on_click=refresh).props("no-caps unelevated")
            else:
                with ui.element("section").classes("metrics"):
                    metric("show_chart", "Produktivitas historis", format_ratio(summary.mean_historical_productivity),
                           "Rata-rata aktual historis", "blue")
                    metric("dataset", "Catatan produksi", format_count(summary.historical_records),
                           "Data historis dari API", "aqua")
                    metric("fact_check", "Prediksi tersimpan", format_count(summary.prediction_count),
                           "Estimasi pra-shift", "purple")
                    metric("memory", "Model aktif", "—" if isinstance(model, ApiError) else model,
                           "Versi model dari API", "amber")
            if isinstance(predictions, ApiError):
                api_error("Prediksi tersimpan belum dapat dimuat.", predictions)
            elif predictions.items:
                dates = defaultdict(list)
                for record in predictions.items:
                    dates[record.production_date].append(record.predicted_productivity)
                with ui.element("section").classes("panel"):
                    section_title("Tren estimasi per tanggal", f"Diringkas dari {len(predictions.items)} prediksi tersimpan.")
                    trend_chart([(f"{day:%d/%m/%Y}", mean(values)) for day, values in sorted(dates.items())])
                prediction_snapshot(max(predictions.items, key=lambda row: row.created_at))
            else:
                notice("Belum ada prediksi tersimpan.", "Buat prediksi untuk mulai melihat perbandingan target.")
            with ui.expansion("Status sistem", icon="monitor_heart").classes("panel health-panel"):
                if isinstance(health, ApiError):
                    api_error("Status sistem belum dapat diperiksa.", health)
                else:
                    with ui.row().classes("health-grid"):
                        for label, key in (("Backend", "status"), ("Database", "db_status"), ("Model", "model_status")):
                            with ui.column().classes("section-title"):
                                ui.label(label).classes("support")
                                value = health.get(key)
                                ui.label(value if isinstance(value, str) and value.strip() else "Belum dilaporkan")

    await refresh()
