"""ProdPulse AI v1.0 — canonical API/domain schemas.

Semua anggota mengimpor kelas/konstanta ini. Jangan menduplikasi field atau
mengganti nama tanpa persetujuan tim dan update schema_version.

Hanya kerangka kontrak, bukan backend/ML/chatbot lengkap.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SCHEMA_VERSION = "1.0"
API_PREFIX = "/api/v1"
DB_NAME_DEFAULT = "prodpulse_ai"
MODEL_FEATURE_NAMES = (
    "department",
    "team_id",
    "target_productivity",
    "smv_minutes",
    "worker_count",
    "day_of_week",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Department(str, Enum):
    SEWING = "sewing"
    FINISHING = "finishing"


class TargetStatus(str, Enum):
    BELOW_TARGET = "below_target"
    MEETS_OR_EXCEEDS = "meets_or_exceeds_target"


class PredictionRequest(StrictModel):
    production_date: date
    department: Department
    team_id: int = Field(ge=1)
    target_productivity: float = Field(gt=0, le=1)
    smv_minutes: float = Field(gt=0)
    worker_count: float = Field(gt=0)


class PredictionResponse(StrictModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    prediction_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    production_date: date
    department: Department
    team_id: int = Field(ge=1)
    target_productivity: float = Field(gt=0, le=1)
    predicted_productivity: float = Field(ge=0)  # Dataset label mungkin >1; jangan clip.
    gap_percentage_points: float
    target_status: TargetStatus
    prediction_type: Literal["demo_estimate"] = "demo_estimate"
    created_at: datetime


class PredictionListResponse(StrictModel):
    items: list[PredictionResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class EvidenceRef(StrictModel):
    type: Literal["prediction", "historical_summary", "model_info"]
    id: str = Field(min_length=1)


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=2000)
    prediction_id: str | None = None
    conversation_id: str | None = None


class ChatResponse(StrictModel):
    conversation_id: str = Field(min_length=1)
    answer: str
    evidence: list[EvidenceRef] = Field(default_factory=list)
    status: Literal["answered", "insufficient_data", "unavailable"]


class OverviewResponse(StrictModel):
    historical_records: int = Field(ge=0)
    prediction_count: int = Field(ge=0)
    mean_historical_productivity: float | None = None


# ---------------------------------------------------------------------------
# Tambahan kontrak v1.0 (additive, tidak mengubah schema yang sudah ada).
# Wajib direview Rendi (backend), Altaf (frontend), Barra (model info), Ardika.
# ---------------------------------------------------------------------------

ErrorCode = Literal[
    "validation_error",
    "not_found",
    "model_unavailable",
    "database_unavailable",
    "internal_error",
]

# Pemetaan tunggal kode error -> HTTP status (README bagian 4.3).
ERROR_HTTP_STATUS: dict[str, int] = {
    "validation_error": 422,
    "not_found": 404,
    "model_unavailable": 503,
    "database_unavailable": 503,
    "internal_error": 500,
}


class FieldError(StrictModel):
    field: str
    message: str


class ErrorResponse(StrictModel):
    """Format error seragam untuk semua endpoint /api/v1 dan /health."""

    code: ErrorCode
    message: str
    fields: list[FieldError] = Field(default_factory=list)


class HealthResponse(StrictModel):
    """GET /health. Nilai "mock" berarti komponen belum nyata (Sprint 0)."""

    status: Literal["ok", "degraded"]
    db_status: Literal["ok", "unavailable", "mock"]
    model_status: Literal["ok", "unavailable", "mock"]


class ModelMetrics(StrictModel):
    """Metrik validasi dalam satuan rasio. null = belum ada (jangan dikarang)."""

    mae: float | None = None
    rmse: float | None = None
    r2: float | None = None


class ActiveModelResponse(StrictModel):
    """GET /api/v1/models/active."""

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    model_version: str = Field(min_length=1)
    feature_names: list[str]
    metrics: ModelMetrics | None = None
    training_cutoff: date | None = None

    @model_validator(mode="after")
    def _features_match_contract(self) -> "ActiveModelResponse":
        if tuple(self.feature_names) != MODEL_FEATURE_NAMES:
            raise ValueError(
                "feature_names harus sama persis dengan MODEL_FEATURE_NAMES"
            )
        return self


class MetaOptionsResponse(StrictModel):
    """GET /api/v1/meta/options (sumber dropdown form)."""

    departments: list[Department] = Field(min_length=1)
    team_ids: list[Annotated[int, Field(ge=1)]] = Field(min_length=1)


class TeamAnalyticsItem(StrictModel):
    department: Department
    team_id: int = Field(ge=1)
    record_count: int = Field(ge=0)
    mean_actual_productivity: float | None = None
    mean_target_productivity: float | None = None


class TeamAnalyticsResponse(StrictModel):
    """GET /api/v1/analytics/teams. Selalu data historis, bukan prediksi."""

    data_label: Literal["historical_dataset"] = "historical_dataset"
    items: list[TeamAnalyticsItem]


class ActualRequest(StrictModel):
    """POST /api/v1/actuals (fase 2). Nilai > 1 diperbolehkan (data UCI)."""

    prediction_id: str = Field(min_length=1)
    actual_productivity: float = Field(ge=0)
    recorded_at: datetime | None = None


class ActualResponse(StrictModel):
    prediction_id: str = Field(min_length=1)
    actual_productivity: float = Field(ge=0)
    recorded_at: datetime
    data_source: Literal["user_entered"] = "user_entered"


def get_target_comparison(predicted: float, target: float) -> tuple[float, TargetStatus]:
    """Bandingkan nilai rasio; selisih dinyatakan dalam poin persentase."""
    gap_pp = round((predicted - target) * 100, 4)
    status = (
        TargetStatus.BELOW_TARGET
        if predicted < target
        else TargetStatus.MEETS_OR_EXCEEDS
    )
    return gap_pp, status
