"""ProdPulse AI v1.0 — canonical API/domain schemas.

Semua anggota mengimpor kelas/konstanta ini. Jangan menduplikasi field atau
mengganti nama tanpa persetujuan tim dan update schema_version.

Hanya kerangka kontrak, bukan backend/ML/chatbot lengkap.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


def get_target_comparison(predicted: float, target: float) -> tuple[float, TargetStatus]:
    """Bandingkan nilai rasio; selisih dinyatakan dalam poin persentase."""
    gap_pp = round((predicted - target) * 100, 4)
    status = (
        TargetStatus.BELOW_TARGET
        if predicted < target
        else TargetStatus.MEETS_OR_EXCEEDS
    )
    return gap_pp, status
