"""Mock API ProdPulse AI v1.0 untuk Sprint 0 (contract freeze).

Tujuan: Altaf (frontend) dan Ardika (chatbot) bisa mengembangkan terhadap
kontrak yang sama tanpa menunggu MongoDB / model ML / backend Rendi.

PENTING (jangan disalahpahami):
- Ini MOCK. Data disimpan di memori dan hilang saat server restart.
- `predicted_productivity` BUKAN keluaran model ML. Rumusnya hanya
  placeholder deterministik (target - 0.06) dan model_version = "mock-v0".
- Data analytics adalah fixture ILUSTRATIF, bukan data UCI asli.
- Semua response membawa header `X-Mock-API: true`.
- /health melaporkan db_status & model_status = "mock".

Jalankan dari root proyek:
    uvicorn mock_api.app:app --reload --port 8000
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.contracts import (
    API_PREFIX,
    ERROR_HTTP_STATUS,
    MODEL_FEATURE_NAMES,
    ActiveModelResponse,
    ActualRequest,
    ActualResponse,
    ChatRequest,
    ChatResponse,
    Department,
    ErrorResponse,
    EvidenceRef,
    FieldError,
    HealthResponse,
    MetaOptionsResponse,
    OverviewResponse,
    PredictionListResponse,
    PredictionRequest,
    PredictionResponse,
    TeamAnalyticsItem,
    TeamAnalyticsResponse,
    get_target_comparison,
)

MOCK_MODEL_VERSION = "mock-v0"

# Fixture ILUSTRATIF (bukan data UCI). Konsisten: overview diturunkan dari sini.
_TEAM_FIXTURE = [
    TeamAnalyticsItem(
        department=Department.SEWING,
        team_id=1,
        record_count=10,
        mean_actual_productivity=0.70,
        mean_target_productivity=0.75,
    ),
    TeamAnalyticsItem(
        department=Department.SEWING,
        team_id=2,
        record_count=12,
        mean_actual_productivity=0.80,
        mean_target_productivity=0.80,
    ),
    TeamAnalyticsItem(
        department=Department.FINISHING,
        team_id=1,
        record_count=8,
        mean_actual_productivity=0.75,
        mean_target_productivity=0.70,
    ),
    TeamAnalyticsItem(
        department=Department.FINISHING,
        team_id=2,
        record_count=15,
        mean_actual_productivity=0.72,
        mean_target_productivity=0.75,
    ),
]

_PREDICTIONS: dict[str, PredictionResponse] = {}
_ORDER: list[str] = []  # urutan pembuatan (terlama -> terbaru)
_ACTUALS: dict[str, ActualResponse] = {}


def reset_store() -> None:
    """Kosongkan state memori (dipakai test)."""
    _PREDICTIONS.clear()
    _ORDER.clear()
    _ACTUALS.clear()


class ApiError(Exception):
    def __init__(self, code: str, message: str, fields: list[FieldError] | None = None):
        self.code = code
        self.message = message
        self.fields = fields or []


app = FastAPI(
    title="ProdPulse AI MOCK API",
    version="1.0-mock",
    description="MOCK Sprint 0: bukan backend asli, bukan output ML.",
)


@app.middleware("http")
async def _mark_mock(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Mock-API"] = "true"
    return response


def _error_json(code: str, message: str, fields: list[FieldError] | None = None):
    body = ErrorResponse(code=code, message=message, fields=fields or [])
    return JSONResponse(status_code=ERROR_HTTP_STATUS[code], content=body.model_dump(mode="json"))


@app.exception_handler(ApiError)
async def _api_error_handler(_: Request, exc: ApiError):
    return _error_json(exc.code, exc.message, exc.fields)


@app.exception_handler(RequestValidationError)
async def _validation_handler(_: Request, exc: RequestValidationError):
    fields = [
        FieldError(
            field=".".join(str(p) for p in err["loc"] if p not in ("body", "query")) or "body",
            message=str(err["msg"]),
        )
        for err in exc.errors()
    ]
    return _error_json("validation_error", "Payload tidak valid.", fields)


# ----------------------------------------------------------------- endpoints


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", db_status="mock", model_status="mock")


@app.get(f"{API_PREFIX}/meta/options", response_model=MetaOptionsResponse)
def meta_options():
    return MetaOptionsResponse(
        departments=[Department.SEWING, Department.FINISHING],
        team_ids=list(range(1, 13)),
    )


@app.get(f"{API_PREFIX}/models/active", response_model=ActiveModelResponse)
def models_active():
    # metrics sengaja None: tidak ada metrik nyata pada mock.
    return ActiveModelResponse(
        model_version=MOCK_MODEL_VERSION,
        feature_names=list(MODEL_FEATURE_NAMES),
        metrics=None,
    )


@app.post(f"{API_PREFIX}/predictions", response_model=PredictionResponse, status_code=201)
def create_prediction(payload: PredictionRequest):
    predicted = max(0.0, round(payload.target_productivity - 0.06, 4))  # PLACEHOLDER, bukan ML
    gap, status = get_target_comparison(predicted, payload.target_productivity)
    result = PredictionResponse(
        prediction_id=str(uuid.uuid4()),
        model_version=MOCK_MODEL_VERSION,
        production_date=payload.production_date,
        department=payload.department,
        team_id=payload.team_id,
        target_productivity=payload.target_productivity,
        predicted_productivity=predicted,
        gap_percentage_points=gap,
        target_status=status,
        created_at=datetime.now(timezone.utc),
    )
    _PREDICTIONS[result.prediction_id] = result
    _ORDER.append(result.prediction_id)
    return result


@app.get(f"{API_PREFIX}/predictions/{{prediction_id}}", response_model=PredictionResponse)
def get_prediction(prediction_id: str):
    found = _PREDICTIONS.get(prediction_id)
    if found is None:
        raise ApiError("not_found", f"Prediksi {prediction_id} tidak ditemukan.")
    return found


@app.get(f"{API_PREFIX}/predictions", response_model=PredictionListResponse)
def list_predictions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    newest_first = list(reversed(_ORDER))
    page = newest_first[offset : offset + limit]
    return PredictionListResponse(
        items=[_PREDICTIONS[i] for i in page],
        total=len(newest_first),
        limit=limit,
        offset=offset,
    )


@app.get(f"{API_PREFIX}/analytics/overview", response_model=OverviewResponse)
def analytics_overview():
    total = sum(t.record_count for t in _TEAM_FIXTURE)
    weighted = sum(t.record_count * (t.mean_actual_productivity or 0) for t in _TEAM_FIXTURE)
    return OverviewResponse(
        historical_records=total,
        prediction_count=len(_PREDICTIONS),
        mean_historical_productivity=round(weighted / total, 4) if total else None,
    )


@app.get(f"{API_PREFIX}/analytics/teams", response_model=TeamAnalyticsResponse)
def analytics_teams():
    return TeamAnalyticsResponse(items=_TEAM_FIXTURE)


@app.post(f"{API_PREFIX}/actuals", response_model=ActualResponse, status_code=201)
def record_actual(payload: ActualRequest):
    if payload.prediction_id not in _PREDICTIONS:
        raise ApiError("not_found", f"Prediksi {payload.prediction_id} tidak ditemukan.")
    result = ActualResponse(
        prediction_id=payload.prediction_id,
        actual_productivity=payload.actual_productivity,
        recorded_at=payload.recorded_at or datetime.now(timezone.utc),
    )
    _ACTUALS[payload.prediction_id] = result
    return result


@app.post(f"{API_PREFIX}/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    """Chat MOCK: template jawaban dari prediksi tersimpan, BUKAN LLM."""
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    found = _PREDICTIONS.get(payload.prediction_id) if payload.prediction_id else None
    if found is None:
        return ChatResponse(
            conversation_id=conversation_id,
            answer=(
                "Data prediksi untuk pertanyaan ini tidak ditemukan, "
                "sehingga saya tidak bisa menjawab dengan angka."
            ),
            evidence=[],
            status="insufficient_data",
        )
    answer = (
        f"[MOCK] Menurut prediksi tersimpan, estimasi "
        f"{found.predicted_productivity * 100:.1f}% dengan selisih "
        f"{found.gap_percentage_points:+.1f} poin persentase terhadap target "
        f"{found.target_productivity * 100:.1f}%. Ini estimasi, bukan hasil aktual, "
        f"dan belum membuktikan penyebab."
    )
    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer,
        evidence=[EvidenceRef(type="prediction", id=found.prediction_id)],
        status="answered",
    )
