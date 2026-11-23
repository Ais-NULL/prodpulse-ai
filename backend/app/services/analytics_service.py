from backend.app.database import get_db


def summarize(query):
    rows = get_db().production_records.aggregate([
        {"$match": query},
        {"$group": {"_id": None, "records": {"$sum": 1}, "mean": {"$avg": "$actual_productivity"}}},
    ])
    return next(rows, {"records": 0, "mean": None})


def overview():
    history = summarize({})
    return {"historical_records": history["records"], "mean_historical_productivity": history["mean"],
            "prediction_count": get_db().predictions.count_documents({})}


def team_history(record):
    return summarize({"team_id": record["team_id"], "department": record["department"],
                      "production_date": {"$lte": record["production_date"]}, "data_source": "uci_597"})
