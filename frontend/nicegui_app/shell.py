"""Navigation, session state, and shared page primitives."""

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from urllib.parse import urlencode

from nicegui import app, ui

from frontend.api_client import ApiClient, ApiError
from frontend.client_config import create_api
from frontend.formatters import FIELD_LABELS
from shared.contracts import ChatResponse

OVERVIEW = "/"
PREDICTION = "/prediction"
HISTORY = "/history"
ASSISTANT = "/assistant"
STYLE = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
PAGES = (
    (OVERVIEW, "Overview", "space_dashboard"),
    (PREDICTION, "Prediksi baru", "add_chart"),
    (HISTORY, "Riwayat prediksi", "history"),
    (ASSISTANT, "AI Assistant", "chat_bubble_outline"),
)

API_MESSAGES = {
    "timeout": "Waktu tunggu backend habis.",
    "connection": "Frontend tidak dapat terhubung ke backend.",
    "transport": "Permintaan ke backend gagal dikirim.",
    "validation": "Backend menolak input (HTTP 422).",
    "unavailable": "Layanan sedang tidak tersedia (HTTP 503).",
    "not_found": "Data atau layanan belum ditemukan (HTTP 404).",
    "http": "Backend mengembalikan kesalahan.",
    "invalid_response": "Respons backend tidak sesuai kontrak.",
}


@dataclass
class Conversation:
    conversation_id: str | None = None
    turns: list[tuple[str, ChatResponse | ApiError]] = field(default_factory=list)


@dataclass
class WorkspaceSession:
    api: ApiClient
    draft: dict = field(default_factory=dict)
    result_id: str | None = None
    conversations: dict[str | None, Conversation] = field(default_factory=dict)
    submitting: bool = False
    sending: set[str | None] = field(default_factory=set)


def session() -> WorkspaceSession:
    tab = app.storage.tab
    if "workspace" not in tab:
        tab["workspace"] = WorkspaceSession(create_api())
    return tab["workspace"]


def prediction_url(route: str, prediction_id: str) -> str:
    return f"{route}?{urlencode({'prediction_id': prediction_id})}"


def action_link(label, target, icon=None, *, primary=False):
    with ui.link(target=target).classes("action-link primary-link" if primary else "action-link") as link:
        if icon:
            ui.icon(icon, size="18px")
        ui.label(label)
    return link


def section_title(text, description=None):
    with ui.column().classes("section-title"):
        ui.html(escape(text), tag="h2").classes("section-name")
        if description:
            ui.label(description).classes("support")


def notice(title, description=None, *, tone="info", icon=None):
    with ui.row().classes(f"notice {tone}").props(
        'role="alert"' if tone == "error" else 'role="status"'
    ):
        ui.icon(icon or {"error": "error_outline", "success": "check_circle_outline"}.get(
            tone, "info_outline"
        ), size="20px")
        with ui.column().classes("section-title"):
            ui.label(title).classes("notice-title")
            if description:
                ui.label(description)


def api_error(title, error):
    fields = [FIELD_LABELS[field] for field in error.fields if field in FIELD_LABELS]
    message = API_MESSAGES[error.kind]
    if fields:
        message += " Periksa " + ", ".join(fields) + "."
    notice(title, message, tone="error")


def loading(message):
    with ui.row().classes("loading-state").props('role="status"'):
        ui.spinner(size="20px", color="primary")
        ui.label(message)


def shell(active, title, description, *, is_mock):
    ui.add_css(STYLE)
    ui.colors(primary="#414ac1")
    drawer = ui.left_drawer(value=False, bordered=True, top_corner=True, bottom_corner=True).props(
        "width=232 breakpoint=1023 show-if-above"
    ).classes("sidebar")
    with drawer:
        ui.link(target=OVERVIEW).classes("brand").props('aria-label="ProdPulse AI, Overview"')
        ui.button(icon="close", on_click=drawer.hide).props(
            'flat round aria-label="Tutup menu utama"'
        ).classes("menu-close")
        with ui.element("nav").classes("nav").props('aria-label="Menu utama"'):
            ui.label("Ruang kerja").classes("nav-caption")
            for path, label, icon in PAGES:
                with ui.link(target=path).classes("nav-link active" if path == active else "nav-link") as link:
                    if path == active:
                        link.props('aria-current="page"')
                    ui.icon(icon, size="19px")
                    ui.label(label)
        with ui.element("aside").classes("sidebar-note"):
            ui.icon("science", size="18px")
            ui.label("Prototipe akademik")
    with ui.header().classes("topbar"):
        ui.button(icon="menu", on_click=drawer.show).props(
            'flat round aria-label="Buka menu utama"'
        ).classes("menu-toggle")
        ui.label("ProdPulse AI").classes("mobile-brand")
        with ui.row().classes("breadcrumb"):
            ui.label("Ruang kerja")
            ui.icon("chevron_right", size="16px")
            ui.label(next(label for path, label, _ in PAGES if path == active)).classes("crumb-current")
        with ui.row().classes("mock-badge" if is_mock else "mode-badge"):
            ui.icon("science", size="15px")
            ui.label("MOCK DATA" if is_mock else "DEMO")
    workspace = ui.element("div").classes("workspace")
    with workspace, ui.element("div").classes("page-intro"):
        ui.html(escape(title), tag="h1")
        ui.label(description).classes("support")
    return workspace
