from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from shared.contracts import ERROR_HTTP_STATUS, ErrorCode, ErrorResponse, FieldError

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from backend.app.database import ensure_indexes, get_db
from backend.app.routes import analytics, chat, metadata, predictions
from backend.app.services.prediction_service import active_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_indexes()
    except PyMongoError:
        pass  # MongoDB mati saat start: /health yang melaporkan, jangan crash
    yield


app = FastAPI(title="ProdPulse AI", lifespan=lifespan)

for router in (predictions.router, analytics.router, metadata.router, chat.router):
    app.include_router(router)


def error_response(code: ErrorCode, message: str, fields: list[FieldError] | None = None):
    body = ErrorResponse(code=code, message=message, fields=fields or [])
    return JSONResponse(status_code=ERROR_HTTP_STATUS[code], content=body.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    fields = [
        FieldError(field=".".join(str(part) for part in err["loc"][1:]) or "body", message=err["msg"])
        for err in exc.errors()
    ]
    return error_response("validation_error", "Periksa kembali kolom yang ditandai.", fields)


@app.exception_handler(HTTPException)
async def api_error(request, exc):
    if exc.status_code == 404:
        return error_response("not_found", str(exc.detail))
    if exc.status_code == 503:
        return error_response("model_unavailable", str(exc.detail))
    return await http_exception_handler(request, exc)


@app.exception_handler(PyMongoError)
async def database_error(request, exc):
    return error_response("database_unavailable", "MongoDB tidak tersedia atau operasi penyimpanan gagal.")


@app.get("/health")
def health():
    try:
        get_db().command("ping")
        db = "ok"
    except PyMongoError:
        db = "unavailable"
    try:
        active_model()
        model = "ok"
    except HTTPException:
        model = "unavailable"
    return {
        "status": "ok" if db == model == "ok" else "degraded",
        "db_status": db,
        "model_status": model,
    }