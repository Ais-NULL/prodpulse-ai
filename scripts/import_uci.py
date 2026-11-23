"""Script ETL idempoten untuk mengimpor dataset UCI #597 ke MongoDB prodpulse_ai."""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, UpdateOne

from shared.contracts import DB_NAME_DEFAULT
from shared.normalization import normalize_uci_row

RAW_CSV_PATH = Path("data/garments_worker_productivity.csv")


def import_uci_to_mongodb(csv_path: Path = RAW_CSV_PATH) -> dict[str, int]:
    load_dotenv()
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB_NAME", DB_NAME_DEFAULT)

    if not csv_path.exists():
        raise FileNotFoundError(f"File CSV tidak ditemukan di {csv_path}")

    raw_df = pd.read_csv(csv_path)
    operations = []

    for idx, row in raw_df.iterrows():
        source_id = f"uci_597_{idx + 1:04d}"
        doc = normalize_uci_row(row.to_dict(), source_record_id=source_id)
        operations.append(
            UpdateOne(
                {"source_record_id": source_id},
                {"$set": doc},
                upsert=True,
            )
        )

    client = MongoClient(mongo_uri)
    try:
        db = client[db_name]
        collection = db["production_records"]

        # Pastikan index sesuai kontrak database v1
        collection.create_index([("source_record_id", ASCENDING)], unique=True)
        collection.create_index(
            [("production_date", ASCENDING), ("department", ASCENDING), ("team_id", ASCENDING)]
        )

        result = collection.bulk_write(operations, ordered=False)
        summary = {
            "total_csv_rows": len(raw_df),
            "upserted_count": result.upserted_count,
            "modified_count": result.modified_count,
            "matched_count": result.matched_count,
        }
        print("Impor UCI selesai:", summary)
        return summary
    finally:
        client.close()


if __name__ == "__main__":
    import_uci_to_mongodb()