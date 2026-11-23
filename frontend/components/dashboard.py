"""Reference-shaped dashboard summary and status tiles."""

from html import escape

import streamlit as st

from frontend.api_client import ApiError

ICONS = {
    "history": "trending_up",
    "predictions": "description",
    "productivity": "bar_chart",
    "model": "memory",
    "health": "monitor_heart",
    "check": "verified",
}


def _icon(name: str) -> str:
    return f'<span class="pp-symbol" aria-hidden="true">{ICONS[name]}</span>'


def dashboard_metrics(*cards: tuple[str, str, str, str]) -> None:
    items = "".join(
        f'<div class="pp-kpi"><dt>{escape(label)}</dt>'
        f'<dd class="pp-stat-value">{escape(value)}<span class="pp-stat-icon pp-stat-icon--{icon}">'
        f'{_icon(icon)}</span></dd><dd class="pp-kpi-note">{escape(note)}</dd></div>'
        for label, value, note, icon in cards
    )
    st.html(f'<dl class="pp-kpis pp-kpis--overview">{items}</dl>')


def status_tiles(health: dict | ApiError) -> None:
    tiles = []
    for label, field, icon in (("API Health", "status", "health"), ("Model Status", "model_status", "check")):
        value = health.get(field) if isinstance(health, dict) else None
        fallback = "Tidak terjangkau" if isinstance(health, ApiError) and field == "status" else "Belum diketahui"
        status = value.strip() if isinstance(value, str) and value.strip() else fallback
        tiles.append(
            f'<div class="pp-status-tile"><dt>{label}</dt><dd>{escape(status)}</dd>'
            f'<span class="pp-status-icon pp-status-icon--{icon}">{_icon(icon)}</span></div>'
        )
    st.html(f'<dl class="pp-status-list">{"".join(tiles)}</dl>')
