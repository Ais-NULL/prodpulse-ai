"""State shared by the Streamlit entry point and its pages."""

import os
from pathlib import Path
from time import monotonic

import streamlit as st
from dotenv import dotenv_values

from frontend.api_client import ApiClient, ApiError
from frontend.mock_api import MockApiClient
from frontend.routes import ASSISTANT_PAGE
from shared.contracts import PredictionResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HEALTH_TTL_SECONDS = 20


def get_api() -> ApiClient:
    if "api_client" not in st.session_state:
        config = dotenv_values(PROJECT_ROOT / ".env")
        mode = os.getenv("PRODPULSE_FRONTEND_MODE", config.get("PRODPULSE_FRONTEND_MODE") or "api")
        base_url = os.getenv("API_BASE_URL", config.get("API_BASE_URL") or "http://localhost:8000")
        if mode.strip().lower() == "mock":
            st.session_state.api_client = MockApiClient()
        else:
            st.session_state.api_client = ApiClient(base_url.strip() or "http://localhost:8000")
    return st.session_state.api_client


def invalidate_health() -> None:
    st.session_state.pop("health_snapshot", None)


def get_health():
    snapshot = st.session_state.get("health_snapshot")
    if snapshot is None or monotonic() - snapshot[0] >= HEALTH_TTL_SECONDS:
        try:
            data = get_api().get_health()
        except ApiError as exc:
            data = exc
        snapshot = (monotonic(), data)
        st.session_state.health_snapshot = snapshot
    return snapshot[1]


def discuss_prediction(prediction: PredictionResponse) -> None:
    st.session_state.chat_prediction = prediction
    st.switch_page(ASSISTANT_PAGE)
