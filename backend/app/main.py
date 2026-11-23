from pathlib import Path
from fastapi import FastAPI
from pymongo import MongoClient
from dotenv import load_dotenv
from backend.app.routes import predictions 

load_dotenv()

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app.include_router(predictions.router) 

app = FastAPI(title="ProdPulse AI")
for router in (predictions.router, analytics.router, metadata.router, chat.router):
    app.include_router(router)


@app.exception_handler(PyMongoError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "MongoDB tidak tersedia atau operasi penyimpanan gagal."})


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
    return {"status": "ok" if db == model == "ok" else "degraded",
            "db_status": db, "model_status": model}
