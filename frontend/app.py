"""ProdPulse AI Streamlit entry point."""

import sys
from pathlib import Path

import streamlit as st

FRONTEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = str(FRONTEND_DIR.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from frontend.components.shell import show_sidebar, show_topbar
from frontend.routes import ASSISTANT_PAGE, HISTORY_PAGE, OVERVIEW_PAGE, PREDICTION_PAGE
from frontend.session import get_api, get_health

st.set_page_config(page_title="ProdPulse AI", layout="wide", initial_sidebar_state="auto")
st.html(FRONTEND_DIR / "styles.css")

pages = [
    st.Page(OVERVIEW_PAGE, title="Overview", icon=":material/home:", default=True),
    st.Page(PREDICTION_PAGE, title="New Prediction", icon=":material/add_chart:"),
    st.Page(HISTORY_PAGE, title="Prediction History", icon=":material/history:"),
    st.Page(ASSISTANT_PAGE, title="AI Assistant", icon=":material/chat_bubble:"),
]
current_page = st.navigation(pages, position="hidden")
show_sidebar(pages, current_page)
show_topbar(pages, get_health(), is_mock=get_api().is_mock)
current_page.run()
