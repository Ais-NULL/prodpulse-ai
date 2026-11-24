"""Build the frontend client from local configuration."""

import os
from pathlib import Path

from dotenv import dotenv_values

from frontend.api_client import ApiClient
from frontend.mock_api import MockApiClient

DEFAULT_API_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_api() -> ApiClient:
    config = dotenv_values(PROJECT_ROOT / ".env")
    mode = os.getenv("PRODPULSE_FRONTEND_MODE", config.get("PRODPULSE_FRONTEND_MODE") or "api")
    base_url = os.getenv("API_BASE_URL", config.get("API_BASE_URL") or DEFAULT_API_URL)
    if mode.strip().lower() == "mock":
        return MockApiClient()
    return ApiClient(base_url.strip() or DEFAULT_API_URL)
