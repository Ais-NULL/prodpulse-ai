import os
from functools import lru_cache
from pymongo import MongoClient, ASCENDING, DESCENDING

@lru_cache(maxsize=1)
def client():
    return MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=1500)

def get_db():
    return client()[os.getenv("MONGODB_DB_NAME", "prodpulse_ai")]

@lru_cache(maxsize=1)
def ensure_indexes():
    db = get_db()
    db.production_records.create_index("source_record_id", unique=True)
    db.production_records.create_index(
        [("production_date", ASCENDING), ("department", ASCENDING), ("team_id", ASCENDING)])
    db.predictions.create_index("prediction_id", unique=True)
    db.predictions.create_index([("created_at", DESCENDING)])
    db.chat_sessions.create_index("conversation_id", unique=True)
