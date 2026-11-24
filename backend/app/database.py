import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient

# .env berada di root repo: backend/app/database.py -> parents[2]
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_client = None


def get_db():
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    return _client[os.getenv("MONGODB_DB_NAME", "prodpulse_ai")]


def ensure_indexes():
    db = get_db()
    db.production_records.create_index("source_record_id", unique=True)
    db.production_records.create_index(
        [("production_date", ASCENDING), ("department", ASCENDING), ("team_id", ASCENDING)]
    )
    db.predictions.create_index("prediction_id", unique=True)
    db.predictions.create_index([("created_at", DESCENDING)])
    db.chat_sessions.create_index("conversation_id", unique=True)