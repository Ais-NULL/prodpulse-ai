import os
from pymongo import MongoClient, ASCENDING, DESCENDING

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=3000)
    return _client[os.getenv("MONGODB_DB_NAME", "prodpulse_ai")]

def ensure_indexes():
    db = get_db()
    db.production_records.create_index("source_record_id", unique=True)
    db.production_records.create_index(
        [("production_date", ASCENDING), ("department", ASCENDING), ("team_id", ASCENDING)])
    db.predictions.create_index("prediction_id", unique=True)
    db.predictions.create_index([("created_at", DESCENDING)])
    db.chat_sessions.create_index("conversation_id", unique=True)