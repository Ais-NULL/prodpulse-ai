from datetime import datetime, timezone
from fastapi import APIRouter
from shared.contracts import API_PREFIX, ChatRequest, ChatResponse
from assistant.service import chat
from backend.app.database import get_db, ensure_indexes
from backend.app.services.analytics_service import team_history
from backend.app.services.prediction_service import get_prediction_by_id

router = APIRouter(prefix=API_PREFIX, tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def answer(body: ChatRequest):
    result = chat(body, get_prediction_by_id=get_prediction_by_id, get_team_history_summary=team_history)
    ensure_indexes()
    now = datetime.now(timezone.utc)
    turn = {"message": body.message, "prediction_id": body.prediction_id, "created_at": now,
            **result.model_dump(mode="json", exclude={"conversation_id"})}
    get_db().chat_sessions.update_one({"conversation_id": result.conversation_id},
                                     {"$setOnInsert": {"created_at": now}, "$push": {"messages": turn}}, upsert=True)
    return result
