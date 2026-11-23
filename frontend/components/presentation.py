"""Reusable page headings and dashboard surfaces."""

from html import escape

import streamlit as st

from frontend.session import get_api


def page_header(title: str, description: str, *, overview: bool = False) -> None:
    description_markup = (
        f'<p class="pp-page-description">{escape(description)}</p>'
        if not overview else ""
    )
    mode_markup = '<span class="pp-mock">MOCK DATA</span>' if get_api().is_mock else ""
    st.html(
        '<header class="pp-header">'
        f'<div class="pp-title-row"><h1>{escape(title)}</h1>'
        f'<span class="pp-breadcrumb"><span class="pp-symbol" aria-hidden="true">home</span> '
        'Home <span aria-hidden="true">›</span> '
        f'{"Dashboard" if overview else escape(title)}</span>'
        f'<span class="pp-page-meta">{mode_markup}'
        '<span class="pp-prototype">DEMO / Academic Prototype</span></span></div>'
        f'{description_markup}</header>'
    )


def metrics(*cards: tuple[str, str, str]) -> None:
    items = "".join(
        f'<div class="pp-kpi"><dt>{escape(label)}</dt><dd>{escape(value)}</dd>'
        f'<dd class="pp-kpi-note">{escape(note)}</dd></div>'
        for label, value, note in cards
    )
    st.html(f'<dl class="pp-kpis pp-kpis--result">{items}</dl>')


def panel_heading(title: str) -> None:
    st.html(f'<h2 class="pp-panel-heading">{escape(title)}</h2>')


def plain_text(text: str) -> None:
    st.html(f'<p class="pp-message">{escape(text)}</p>')
