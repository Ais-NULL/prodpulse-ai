"""In-memory fixtures for explicitly enabled frontend development sessions."""

import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from uuid import uuid4

from frontend.api_client import ApiClient, ApiError
from frontend.mock_analytics import SAMPLE_ROWS
from shared.contracts import (
    ChatRequest,
    ChatResponse,
    EvidenceRef,
    OverviewResponse,
    PredictionListResponse,
    PredictionRequest,
    PredictionResponse,
    get_target_comparison,
)

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class MockApiClient(ApiClient):
    is_mock = True

    def __init__(self) -> None:
        example_path = EXAMPLES / "prediction_response_example_only.json"
        example = json.loads(example_path.read_text(encoding="utf-8"))
        self.example = PredictionResponse.model_validate(example)
        self.predictions = {self.example.prediction_id: self.example}

    def get_health(self) -> dict[str, str]:
        return {"status": "Simulasi", "db_status": "Simulasi", "model_status": "Simulasi"}

    def get_model_version(self) -> str:
        return self.example.model_version

    def get_overview(self) -> OverviewResponse:
        return OverviewResponse(
            historical_records=len(SAMPLE_ROWS),
            prediction_count=len(self.predictions),
            mean_historical_productivity=mean(value for _, _, value in SAMPLE_ROWS),
        )

    def create_prediction(self, body: PredictionRequest) -> PredictionResponse:
        estimate = self.example.predicted_productivity
        gap, status = get_target_comparison(estimate, body.target_productivity)
        response = PredictionResponse(
            **body.model_dump(exclude={"smv_minutes", "worker_count"}),
            prediction_id=str(uuid4()),
            model_version=self.get_model_version(),
            predicted_productivity=estimate,
            gap_percentage_points=gap,
            target_status=status,
            created_at=datetime.now(UTC),
        )
        self.predictions[response.prediction_id] = response
        return response

    def list_predictions(self, *, limit: int, offset: int) -> PredictionListResponse:
        records = list(reversed(self.predictions.values()))
        return PredictionListResponse(
            items=records[offset : offset + limit], total=len(records), limit=limit, offset=offset
        )

    def get_prediction(self, prediction_id: str) -> PredictionResponse:
        try:
            return self.predictions[prediction_id]
        except KeyError as exc:
            raise ApiError("not_found", 404) from exc

    def chat(self, body: ChatRequest) -> ChatResponse:
        conversation_id = body.conversation_id or str(uuid4())
        if body.prediction_id is None or body.prediction_id not in self.predictions:
            return ChatResponse(
                conversation_id=conversation_id,
                answer="Fixture chat memerlukan prediksi dari sesi mock ini.",
                status="insufficient_data",
            )
        return ChatResponse(
            conversation_id=conversation_id,
            answer="Contoh respons untuk menguji tampilan referensi prediksi.",
            evidence=[EvidenceRef(type="prediction", id=body.prediction_id)],
            status="answered",
        )
