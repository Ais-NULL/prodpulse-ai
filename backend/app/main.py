from fastapi import FastAPI
from backend.app.routes import predictions, analytics, metadata, chat

app = FastAPI(title="ProdPulse AI")

app.include_router(predictions.router)
app.include_router(analytics.router)
app.include_router(metadata.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok", "db_status": "unknown", "model_status": "unknown"}