from uuid import uuid4

from shared.contracts import ChatRequest, ChatResponse, EvidenceRef, PredictionResponse
from .gemini import ProviderUnavailable, select_topics


def number_id(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def target_summary(record: dict, team: str, date_label: str) -> str:
    estimate = number_id(record["predicted_productivity"] * 100)
    target = number_id(record["target_productivity"] * 100)
    gap = record["gap_percentage_points"]
    if gap == 0:
        return f"{team} diperkirakan tepat mencapai target {target}% pada {date_label}."
    direction = "di bawah" if gap < 0 else "di atas"
    size = number_id(abs(gap))
    if size == "0":
        size = "kurang dari 0,01"
    return (
        f"Produktivitas {team} pada {date_label} diperkirakan {estimate}%. "
        f"Dengan target {target}%, estimasinya {size} poin persentase {direction} target."
    )


def chat(request: ChatRequest, *, get_prediction_by_id, classify=select_topics, get_team_history_summary=None) -> ChatResponse:
    """Read the selected prediction and cite the facts used in each reply."""
    result = ChatResponse(conversation_id=request.conversation_id or str(uuid4()),
                          answer="", status="insufficient_data")
    prediction_id = request.prediction_id
    if not request.message.strip():
        result.answer = "Tulis pertanyaan tentang prediksi tim yang ingin Anda bahas."
        return result
    if not prediction_id:
        result.answer = "Pilih satu prediksi di halaman Riwayat, lalu tanyakan estimasi atau selisihnya dari target."
        return result
    record = get_prediction_by_id(prediction_id)
    if record is None:
        result.answer = "Prediksi ini belum ditemukan. Pilih kembali prediksi yang ingin dibahas di halaman Riwayat."
        return result
    prediction = PredictionResponse.model_validate(record)
    if prediction.prediction_id != prediction_id:
        raise ValueError("ID sumber berbeda dari prediksi yang diminta.")
    try:
        topics = classify(request.message.strip())
    except ProviderUnavailable as error:
        result.status = "unavailable"
        result.answer = str(error)
        return result
    if "unsupported" in topics:
        result.answer = "Untuk prediksi ini, Anda bisa menanyakan estimasi, target, versi model, atau rata-rata produktivitas tim di data UCI."
        return result
    if "individual" in topics:
        result.answer = "Catatan ini merangkum hasil satu tim. Untuk menilai seorang pekerja, diperlukan data per orang."
        return result

    record = prediction.model_dump(mode="json")
    team = f"Tim {record['team_id']} ({record['department'].capitalize()})"
    date_label = prediction.production_date.strftime("%d/%m/%Y")
    paragraphs = []
    if "target" in topics:
        paragraphs.append(target_summary(record, team, date_label))
    if "actual" in topics:
        paragraphs.append("Perkiraan ini dibuat sebelum shift. Produktivitas aktual untuk shift tersebut belum tercatat di prediksi ini.")
    if "cause" in topics:
        paragraphs.append("Dari prediksi ini saja, penyebab selisih dan dampak mengubah rencana kerja belum bisa dipastikan.")
    if "model" in topics:
        paragraphs.append(f"Model yang digunakan untuk prediksi ini adalah {prediction.model_version}.")
    cites_prediction = any(t in topics for t in ("target", "actual", "cause", "model"))
    if cites_prediction:
        result.evidence.append(EvidenceRef(type="prediction", id=prediction_id))
    if "history" in topics:
        summary = get_team_history_summary(record) if get_team_history_summary else None
        if summary and summary["mean"] is not None:
            average = number_id(summary["mean"] * 100)
            paragraphs.append(
                f"Dalam data historis UCI sampai {date_label}, rata-rata produktivitas aktual "
                f"{team} adalah {average}% dari {summary['records']} catatan."
            )
            result.evidence.append(EvidenceRef(
                type="historical_summary", id=f"uci_597:{record['department']}:{record['team_id']}:{record['production_date']}"
            ))
            result.status = "answered"
        else:
            paragraphs.append(f"Belum ada ringkasan historis UCI untuk {team} sampai {date_label}.")
    if any(t in topics for t in ("target", "model")):
        result.status = "answered"
    if cites_prediction:
        paragraphs.append(f"ID prediksi {prediction_id}.")
    result.answer = "\n\n".join(paragraphs)
    return result
