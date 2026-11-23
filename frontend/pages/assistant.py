"""Session-scoped AI Assistant connected to the FastAPI chat endpoint."""

from dataclasses import dataclass, field

import streamlit as st

from frontend.api_client import ApiError
from frontend.components.presentation import page_header, panel_heading, plain_text
from frontend.components.states import show_api_error
from frontend.formatters import format_gap, format_ratio, prediction_context
from frontend.routes import HISTORY_PAGE
from frontend.session import get_api
from shared.contracts import ChatRequest, ChatResponse, PredictionResponse

EVIDENCE_LABELS = {
    "prediction": "Prediksi",
    "historical_summary": "Ringkasan historis",
    "model_info": "Informasi model",
}


@dataclass
class ChatTurn:
    message: str
    response: ChatResponse | None = None
    error: ApiError | None = None


@dataclass
class Conversation:
    conversation_id: str | None = None
    turns: list[ChatTurn] = field(default_factory=list)


def show_response(turn: ChatTurn, turn_index: int) -> None:
    if turn.error is not None:
        show_api_error(turn.error, "AI Assistant belum dapat menjawab.")
        return
    response = turn.response
    if response is None:
        return
    if response.status == "unavailable":
        st.warning("AI Assistant sedang tidak tersedia. Coba lagi setelah layanan pulih.")
        return
    with st.chat_message("assistant"):
        if response.status == "insufficient_data":
            st.caption("Data untuk menjawab belum cukup.")
        plain_text(response.answer)
        if response.evidence:
            with st.expander("Sumber jawaban"):
                for index, source in enumerate(response.evidence):
                    plain_text(f"{EVIDENCE_LABELS[source.type]}: {source.id}")
                    if source.type == "prediction" and st.button(
                        "Buka detail bukti",
                        key=f"prediction_evidence_{turn_index}_{index}",
                    ):
                        st.session_state.history_source_id = source.id
                        st.switch_page(HISTORY_PAGE)


def remove_context() -> None:
    st.session_state.pop("chat_prediction", None)


def show_context(prediction: PredictionResponse | None) -> None:
    with st.container(key="pp_chat_context"):
        panel_heading("Konteks percakapan")
        if prediction is None:
            st.caption("Belum ada prediksi yang dipilih. Anda dapat mengajukan pertanyaan umum.")
            st.page_link(HISTORY_PAGE, label="Pilih dari riwayat", icon=":material/history:")
        else:
            plain_text(prediction_context(prediction))
            st.caption(
                f"Estimasi {format_ratio(prediction.predicted_productivity)} · "
                f"Target {format_ratio(prediction.target_productivity)} · "
                f"Selisih {format_gap(prediction.gap_percentage_points)}"
            )
            plain_text(f"ID prediksi: {prediction.prediction_id}")
            st.button("Lepas konteks prediksi", on_click=remove_context)


def render_assistant() -> None:
    page_header(
        "AI Assistant",
        "Tanyakan arti hasil estimasi, target, atau data historis yang tersedia.",
    )
    prediction = st.session_state.get("chat_prediction")
    prediction_id = prediction.prediction_id if prediction is not None else None
    show_context(prediction)
    with st.container(key="pp_chat"):
        panel_heading("Percakapan")
        show_conversation(prediction_id)


def show_conversation(prediction_id: str | None) -> None:
    conversations = st.session_state.setdefault("conversations", {})
    if st.button("Hapus percakapan ini", disabled=prediction_id not in conversations):
        conversations.pop(prediction_id, None)
    conversation = conversations.get(prediction_id)
    if conversation:
        for turn_index, turn in enumerate(conversation.turns):
            with st.chat_message("user"):
                plain_text(turn.message)
            show_response(turn, turn_index)
    else:
        st.info("Mulai dengan menanyakan estimasi atau selisih terhadap target.")

    message = st.chat_input("Tulis pertanyaan", max_chars=2000)
    if message is None:
        return
    if not message.strip():
        st.warning("Masukkan pertanyaan sebelum mengirim pesan.")
        return

    conversation = conversations.setdefault(prediction_id, Conversation())
    turn = ChatTurn(message.strip())
    with st.chat_message("user"):
        plain_text(turn.message)
    request = ChatRequest(
        message=turn.message, prediction_id=prediction_id, conversation_id=conversation.conversation_id
    )
    with st.spinner("AI Assistant sedang menyiapkan respons…"):
        try:
            turn.response = get_api().chat(request)
        except ApiError as error:
            turn.error = error
        else:
            conversation.conversation_id = turn.response.conversation_id
    conversation.turns.append(turn)
    show_response(turn, len(conversation.turns) - 1)


render_assistant()
