"""State shared by the Streamlit entry point and its pages."""

from time import monotonic

import streamlit as st

from frontend.api_client import ApiClient, ApiError
from frontend.client_config import create_api
from frontend.routes import ASSISTANT_PAGE
from shared.contracts import PredictionResponse

HEALTH_TTL_SECONDS = 20


def get_api() -> ApiClient:
    if "api_client" not in st.session_state:
        st.session_state.api_client = create_api()
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
