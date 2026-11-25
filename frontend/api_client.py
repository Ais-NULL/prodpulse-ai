"""FastAPI transport and parsing for the contracts consumed by Streamlit."""

from __future__ import annotations

from typing import Any, TypeVar
from urllib.parse import quote

import requests
from pydantic import BaseModel, ValidationError

from shared.contracts import (
    API_PREFIX,
    ChatRequest,
    ChatResponse,
    OverviewResponse,
    PredictionListResponse,
    PredictionRequest,
    PredictionResponse,
)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)
PREDICTIONS_PATH = f"{API_PREFIX}/predictions"


class ApiError(Exception):
    def __init__(
        self,
        kind: str,
        status_code: int | None = None,
        fields: tuple[str, ...] = (),
    ) -> None:
        super().__init__(kind)
        self.kind = kind
        self.status_code = status_code
        self.fields = fields


def _validation_fields(response: requests.Response) -> tuple[str, ...]:
    try:
        payload = response.json()
        if isinstance(payload.get("fields"), list):
            return tuple(dict.fromkeys(
                item["field"] for item in payload["fields"]
                if isinstance(item, dict) and isinstance(item.get("field"), str)
            ))
        detail = payload.get("detail", [])
    except (ValueError, AttributeError):
        return ()
    if not isinstance(detail, list):
        return ()
    fields = []
    for item in detail:
        location = item.get("loc") if isinstance(item, dict) else None
        if isinstance(location, list) and location and isinstance(location[-1], str):
            fields.append(location[-1])
    return tuple(dict.fromkeys(fields))


class ApiClient:
    is_mock = False

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: BaseModel | None = None,
        params: dict[str, int] | None = None,
        timeout: tuple[float, float] = (2, 12),
        allow_degraded_health: bool = False,
    ) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                json=body.model_dump(mode="json") if body is not None else None,
                params=params,
                timeout=timeout,
                allow_redirects=False,
            )
        except requests.Timeout as exc:
            raise ApiError("timeout") from exc
        except requests.ConnectionError as exc:
            raise ApiError("connection") from exc
        except requests.RequestException as exc:
            raise ApiError("transport") from exc

        status = response.status_code
        if status == 422:
            raise ApiError("validation", status, _validation_fields(response))
        if status == 503 and not allow_degraded_health:
            raise ApiError("unavailable", status)
        if not (200 <= status < 300 or allow_degraded_health and status == 503):
            raise ApiError("not_found" if status == 404 else "http", status)

        try:
            data = response.json()
        except ValueError as exc:
            if status == 503:
                raise ApiError("unavailable", status) from exc
            raise ApiError("invalid_response", status) from exc
        if not isinstance(data, dict):
            raise ApiError("unavailable" if status == 503 else "invalid_response", status)
        if allow_degraded_health and not isinstance(data.get("status"), str):
            raise ApiError("unavailable" if status == 503 else "invalid_response", status)
        return data

    @staticmethod
    def _parse(model: type[ResponseModel], data: dict[str, Any]) -> ResponseModel:
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            raise ApiError("invalid_response") from exc

    def get_health(self) -> dict[str, Any]:
        return self._request_json(
            "GET", "/health", timeout=(1, 2), allow_degraded_health=True
        )

    def get_overview(self) -> OverviewResponse:
        data = self._request_json("GET", f"{API_PREFIX}/analytics/overview")
        return self._parse(OverviewResponse, data)

    def get_model_version(self) -> str:
        data = self._request_json("GET", f"{API_PREFIX}/models/active")
        version = data.get("model_version")
        if not isinstance(version, str) or not version.strip():
            raise ApiError("invalid_response")
        return version

    def create_prediction(self, body: PredictionRequest) -> PredictionResponse:
        data = self._request_json("POST", PREDICTIONS_PATH, body=body)
        return self._parse(PredictionResponse, data)

    def list_predictions(self, *, limit: int, offset: int) -> PredictionListResponse:
        data = self._request_json(
            "GET", PREDICTIONS_PATH, params={"limit": limit, "offset": offset}
        )
        return self._parse(PredictionListResponse, data)

    def get_prediction(self, prediction_id: str) -> PredictionResponse:
        data = self._request_json("GET", f"{PREDICTIONS_PATH}/{quote(prediction_id, safe='')}")
        result = self._parse(PredictionResponse, data)
        if result.prediction_id != prediction_id:
            raise ApiError("invalid_response")
        return result

    def chat(self, body: ChatRequest) -> ChatResponse:
        data = self._request_json("POST", f"{API_PREFIX}/chat", body=body, timeout=(2, 30))
        return self._parse(ChatResponse, data)
