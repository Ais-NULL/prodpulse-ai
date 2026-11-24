"""Analytics atas data historis (production_records, bukan data pabrik real-time).

Bentuk return disesuaikan dengan yang dibaca assistant/service.py milik Ardika:
    team_history(record) -> {"records": int, "mean": float | None}
"""
from backend.app.database import get_db


def summarize(query: dict) -> dict:
    rows = get_db().production_records.aggregate([
        {"$match": query},
        {"$group": {"_id": None,
                    "records": {"$sum": 1},
                    "mean": {"$avg": "$actual_productivity"}}},
    ])
    row = next(rows, None)
    if row is None:
        return {"records": 0, "mean": None}  # tidak ada data: None, bukan 0 palsu
    return {"records": row["records"], "mean": row["mean"]}


def overview() -> dict:
    history = summarize({})
    return {
        "historical_records": history["records"],
        "mean_historical_productivity": history["mean"],
        "prediction_count": get_db().predictions.count_documents({}),
    }


def team_history(record: dict) -> dict:
    """Rata-rata aktual historis tim dari record prediksi, sampai tanggal prediksi."""
    return summarize({
        "team_id": record["team_id"],
        "department": str(record["department"]),
        "production_date": {"$lte": str(record["production_date"])},
        "data_source": "uci_597",
    })


def teams_summary() -> dict:
    rows = get_db().production_records.aggregate([
        {"$group": {"_id": {"department": "$department", "team_id": "$team_id"},
                    "records": {"$sum": 1},
                    "mean_actual": {"$avg": "$actual_productivity"},
                    "mean_target": {"$avg": "$target_productivity"}}},
    ])
    items = [{"department": r["_id"]["department"],
              "team_id": r["_id"]["team_id"],
              "records": r["records"],
              "mean_actual": r["mean_actual"],
              "mean_target": r["mean_target"]} for r in rows]
    items.sort(key=lambda x: (str(x["department"]), x["team_id"]))
    return {"items": items}