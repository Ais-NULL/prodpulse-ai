"""Session-scoped conversations backed by the shared chat API."""

from nicegui import run, ui

from frontend.api_client import ApiError
from frontend.formatters import format_gap, format_ratio, prediction_context
from frontend.nicegui_app.shell import (
    ASSISTANT, HISTORY, Conversation, action_link, api_error, loading, notice,
    prediction_url, section_title, session, shell,
)
from shared.contracts import ChatRequest

EVIDENCE_LABELS = {
    "prediction": "Prediksi",
    "historical_summary": "Ringkasan historis",
    "model_info": "Informasi model",
}


def bubble(role, message):
    with ui.row().classes(f"chat-turn {role}"):
        ui.icon("person_outline" if role == "user" else "auto_awesome", size="18px").classes("chat-avatar")
        with ui.column().classes("chat-bubble"):
            ui.label("Anda" if role == "user" else "AI Assistant").classes("bubble-author")
            ui.label(message).classes("bubble-text")


def show_response(response):
    if isinstance(response, ApiError):
        api_error("AI Assistant belum dapat menjawab.", response)
        return
    if response.status == "unavailable":
        notice("AI Assistant sedang tidak tersedia.", "Coba lagi setelah layanan pulih.", tone="error")
        return
    if response.status == "insufficient_data":
        notice("Data untuk menjawab belum cukup.")
    if response.answer:
        bubble("assistant", response.answer)
    if response.evidence:
        with ui.expansion("Sumber jawaban", icon="source").classes("data-expansion evidence-list"):
            for item in response.evidence:
                with ui.column().classes("evidence"):
                    ui.label(f"{EVIDENCE_LABELS[item.type]} · {item.id}")
                    if item.type == "prediction":
                        action_link("Buka detail bukti", prediction_url(HISTORY, item.id), "arrow_forward")


async def assistant_page(prediction_id: str | None = None):
    await ui.context.client.connected()
    state = session()
    workspace = shell(ASSISTANT, "AI Assistant", "Pahami estimasi, target, dan data yang mendukungnya.",
                      is_mock=state.api.is_mock)

    with workspace, ui.element("div").classes("assistant-grid"):
        with ui.element("section").classes("panel chat-panel"):
            with ui.row().classes("panel-head"):
                section_title("Percakapan", "Tanyakan selisih target atau bahas prediksi tertentu.")
                clear = ui.button("Hapus percakapan", icon="delete_outline").props("flat no-caps").classes("row-action")
            with ui.scroll_area().classes("chat-scroll") as scroll:
                chat = ui.column().classes("chat-log").props('role="log" aria-label="Riwayat percakapan"')
            feedback = ui.element("div").classes("feedback-slot")
            with ui.row().classes("composer"):
                message = ui.textarea("Pertanyaan", placeholder="Tulis pertanyaan…").props(
                    'outlined autogrow maxlength=2000'
                )
                send = ui.button("Kirim", icon="send").props("no-caps unelevated").classes("main-button")
        context = ui.element("aside").classes("panel workflow-panel chat-context")
        with context:
            section_title("Konteks percakapan")
            context_body = ui.element("div").classes("section-stack")
        with ui.dialog() as confirm, ui.card().classes("ranking-dialog"):
            section_title("Hapus percakapan ini?", "Riwayat untuk konteks ini akan dihapus dari sesi.")
            with ui.row().classes("form-actions"):
                ui.button("Batal", on_click=confirm.close).props("flat no-caps")
                erase = ui.button("Hapus", color="negative").props("no-caps unelevated")

    context_ready = not prediction_id
    send.set_enabled(context_ready)
    message.set_enabled(context_ready)

    def render_log():
        chat.clear()
        conversation = state.conversations.get(prediction_id)
        clear.set_enabled(bool(conversation and conversation.turns) and prediction_id not in state.sending)
        with chat:
            if conversation and conversation.turns:
                for question, response in conversation.turns:
                    bubble("user", question)
                    show_response(response)
            else:
                with ui.column().classes("chat-empty"):
                    ui.icon("chat_bubble_outline", size="28px").classes("empty-icon")
                    ui.label("Mulai percakapan").classes("record-name")
                    ui.label("Contoh: Apa arti selisih terhadap target?").classes("support")
        scroll.scroll_to(percent=1)

    async def send_question():
        if not context_ready or prediction_id in state.sending:
            return
        question = (message.value or "").strip()
        feedback.clear()
        if not question or len(question) > 2000:
            with feedback:
                notice("Masukkan pertanyaan dengan 1–2.000 karakter.", tone="error")
            return
        conversation = state.conversations.setdefault(prediction_id, Conversation())
        request = ChatRequest(message=question, prediction_id=prediction_id,
                              conversation_id=conversation.conversation_id)
        state.sending.add(prediction_id)
        send.disable()
        clear.disable()
        message.set_value("")
        if not conversation.turns:
            chat.clear()
        with chat:
            bubble("user", question)
            pending = ui.element("div")
            with pending:
                loading("AI Assistant sedang menyiapkan respons…")
        scroll.scroll_to(percent=1)
        try:
            response = await run.io_bound(state.api.chat, request)
        except ApiError as error:
            response = error
        else:
            conversation.conversation_id = response.conversation_id
        finally:
            state.sending.discard(prediction_id)
            send.enable()
        conversation.turns.append((question, response))
        pending.delete()
        with chat:
            show_response(response)
        clear.enable()
        scroll.scroll_to(percent=1)

    def clear_chat():
        if prediction_id in state.sending:
            return
        state.conversations.pop(prediction_id, None)
        confirm.close()
        feedback.clear()
        render_log()

    send.on_click(send_question)
    message.on("keydown.enter.exact.prevent", send_question, args=[])
    clear.on_click(confirm.open)
    erase.on_click(clear_chat)
    render_log()

    if not prediction_id:
        with context_body:
            ui.label("Belum ada prediksi yang dipilih. Anda dapat mengajukan pertanyaan umum.").classes("support")
            action_link("Pilih dari riwayat", HISTORY, "history")
        return

    with context_body:
        loading("Memuat konteks…")
    try:
        record = await run.io_bound(state.api.get_prediction, prediction_id)
    except ApiError as error:
        context_body.clear()
        with context_body:
            api_error("Konteks prediksi belum dapat dimuat.", error)
            action_link("Mulai pertanyaan umum", ASSISTANT, "chat_bubble_outline")
        return
    context_body.clear()
    with context_body:
        ui.label(prediction_context(record)).classes("record-name")
        with ui.element("div").classes("context-values"):
            for name, value in (
                ("Estimasi", format_ratio(record.predicted_productivity)),
                ("Target", format_ratio(record.target_productivity)),
                ("Selisih", format_gap(record.gap_percentage_points)),
            ):
                with ui.column().classes("section-title"):
                    ui.label(name).classes("support")
                    ui.label(value).classes("context-value")
        action_link("Lepas konteks", ASSISTANT, "close")
    context_ready = True
    send.enable()
    message.enable()
