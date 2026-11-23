"""Navigation and utilities shared by all four Streamlit pages."""

from pathlib import Path

import streamlit as st

from frontend.components.states import health_summary
from frontend.session import invalidate_health

SEARCH_KEY = "pp_page_search"
BRAND_LOGO = Path(__file__).resolve().parents[1] / "assets" / "prodpulse-logo.png"


def _queue_page_navigation() -> None:
    st.session_state.pp_search_destination = st.session_state.get(SEARCH_KEY)
    st.session_state[SEARCH_KEY] = None


def show_sidebar(pages, current_page) -> None:
    with st.sidebar:
        with st.container(key="pp_rail", gap="small"):
            for index, page in enumerate(pages):
                state = "active" if page.url_path == current_page.url_path else "idle"
                with st.container(key=f"pp_nav_{index}_{state}"):
                    st.page_link(page, width="stretch")
            st.html('<p class="pp-rail-caption">PRODPULSE AI <span>DEMO</span></p>')


def show_topbar(pages, health, *, is_mock: bool) -> None:
    page_options = {page.title: page for page in pages}
    with st.container(key="pp_topbar"):
        brand, search, alerts, help_col, profile = st.columns(
            [4, 2, 1, 1, 2], gap="small", vertical_alignment="center"
        )
        with brand, st.container(key="pp_brand"):
            st.image(str(BRAND_LOGO), width="stretch")
            st.html('<span class="pp-brand-label">ProdPulse AI</span>')
        with search:
            st.selectbox(
                "Cari halaman", list(page_options), index=None, placeholder="Cari halaman",
                label_visibility="collapsed", key=SEARCH_KEY, on_change=_queue_page_navigation,
            )
        with alerts, st.container(key="pp_utility_status"):
            with st.popover("Status sistem", icon=":material/notifications:"):
                health_summary(health, is_mock=is_mock)
                st.button("Periksa ulang status", on_click=invalidate_health)
        with help_col, st.container(key="pp_utility_help"):
            with st.popover("Bantuan", icon=":material/help:"):
                st.markdown("**Alur kerja ProdPulse AI**")
                st.caption("Buat estimasi pra-shift, tinjau prediksi tersimpan, lalu buka AI Assistant.")
                for page in pages:
                    st.page_link(page)
        profile.html(
            '<div class="pp-profile" aria-label="Operator demo">'
            '<span class="pp-avatar" aria-hidden="true"><i></i></span>'
            '<span class="pp-profile-label">Operator demo</span></div>'
        )

    destination = st.session_state.pop("pp_search_destination", None)
    if destination in page_options:
        st.switch_page(page_options[destination])
