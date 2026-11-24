from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

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

# Route chat berasal dari branch Ardika. Setelah merge, tambahkan:
#   from backend.app.routes import chat
#   dan masukkan chat.router ke tuple di bawah.
for router in (predictions.router, analytics.router, metadata.router, chat.router):
    app.include_router(router)


@app.exception_handler(PyMongoError)
async def database_error(request, exc):
    return JSONResponse(
        status_code=503,
        content={"detail": "MongoDB tidak tersedia atau operasi penyimpanan gagal."},
    )


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