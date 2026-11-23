import os
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

load_dotenv()

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
        [("production_date", ASCENDING), ("department", ASCENDING), ("team_id", ASCENDING)])
    db.predictions.create_index("prediction_id", unique=True)
    db.predictions.create_index([("created_at", DESCENDING)])
    db.chat_sessions.create_index("conversation_id", unique=True)