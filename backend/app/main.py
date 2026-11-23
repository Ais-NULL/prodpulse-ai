import os
from pathlib import Path
from fastapi import FastAPI
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ProdPulse AI")


def check_db() -> str:
    try:
        client = MongoClient(
            os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            serverSelectionTimeoutMS=1500,
        )
        client.admin.command("ping")
        return "ok"
    except Exception:
        return "unavailable"


def check_model() -> str:
    path = Path(os.getenv("MODEL_ARTIFACT_PATH", "ml/artifacts/model.joblib"))
    return "ok" if path.exists() else "unavailable"


@app.get("/health")
def health():
    db = check_db()
    model = check_model()
    return {
        "status": "ok" if db == "ok" and model == "ok" else "degraded",
        "db_status": db,
        "model_status": model,
    }