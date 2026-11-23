from uuid import uuid4
from shared.contracts import ChatRequest, ChatResponse, EvidenceRef, PredictionResponse
from .gemini import ProviderUnavailable, select_topics


def chat(request: ChatRequest, *, get_prediction_by_id, classify=select_topics, get_team_history_summary=None) -> ChatResponse:
    """Reader tepercaya mengembalikan PredictionResponse, mapping v1 atau None."""
    result = ChatResponse(conversation_id=request.conversation_id or str(uuid4()),
                          answer="", status="insufficient_data")
    prediction_id = request.prediction_id
    if not request.message.strip():
        result.answer = "Isi pertanyaan terlebih dahulu."
        return result
    if not prediction_id:
        result.answer = "Pilih satu prediksi dulu supaya saya bisa membaca datanya."
        return result
    record = get_prediction_by_id(str(prediction_id))
    if record is None:
        result.answer = "Prediksi dengan ID tersebut belum ditemukan."
        return result
    record = PredictionResponse.model_validate(record).model_dump(mode="json")
    if str(record["prediction_id"]) != str(prediction_id):
        raise ValueError("ID sumber berbeda dari prediksi yang diminta.")
    try:
        topics = classify(request.message.strip())
    except ProviderUnavailable as error:
        result.status = "unavailable"
        result.answer = str(error)
        return result
    if "unsupported" in topics:
        result.answer = "Saya bisa menjelaskan estimasi, target dan versi model pada prediksi yang dipilih."
        return result
    if "individual" in topics:
        result.answer = "Data tersedia pada tingkat tim. Penilaian pekerja individu tidak tersedia."
        return result

    sentences = []
    if "target" in topics:
        gap = record["gap_percentage_points"]
        if gap == 0:
            comparison = "tepat sesuai target"
        else:
            direction = "di bawah" if gap < 0 else "di atas"
            comparison = f"{round(abs(gap), 2)} poin persentase {direction} target"
        sentences.append(
            f"Estimasi Tim {record['team_id']} ({record['department']}) pada {record['production_date']} "
            f"sebesar {round(record['predicted_productivity'] * 100, 2)}% dengan target "
            f"{round(record['target_productivity'] * 100, 2)}%, {comparison}."
        )
    if "actual" in topics:
        sentences.append("Catatan ini berisi estimasi sebelum shift. Realisasi shift belum tersedia di sini.")
    if "cause" in topics:
        sentences.append("Catatan prediksi ini belum menyediakan bukti penyebab selisih atau dampak perubahan rencana.")
    if "model" in topics:
        sentences.append(f"Versi model pada prediksi ini adalah {record['model_version']}. "
                         "Catatan prediksi ini memuat versi model.")
    history_ref = None
    if "history" in topics:
        summary = get_team_history_summary(record) if get_team_history_summary else None
        if summary and summary["mean"] is not None:
            scope = f"Tim {record['team_id']} {record['department']} sampai {record['production_date']}"
            sentences.append(f"Rata-rata aktual UCI untuk {scope} adalah {summary['mean']:.2%} dari {summary['records']} catatan.")
            history_ref = EvidenceRef(type="historical_summary", id=f"uci_597:{record['department']}:{record['team_id']}:{record['production_date']}")
        else:
            sentences.append("Riwayat UCI untuk tim dan departemen ini belum tersedia.")
    if any(t in topics for t in ("target", "actual", "cause", "model")):
        source_id = str(record["prediction_id"])
        result.evidence = [EvidenceRef(type="prediction", id=source_id)]
        sentences.append(f"ID prediksi {source_id}.")
    if history_ref:
        result.evidence.append(history_ref)
    if history_ref or "model" in topics or "target" in topics:
        result.status = "answered"
    result.answer = " ".join(sentences)
    return result
