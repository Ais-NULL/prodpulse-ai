"""Chat read-only atas CSV UCI dan hasil inference holdout milik tim."""
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean
from uuid import uuid4

from dotenv import load_dotenv
from shared.contracts import ChatResponse, EvidenceRef, get_target_comparison
from shared.normalization import normalize_uci_row, normalize_department, parse_uci_date
from .gemini import ProviderUnavailable, select_topics

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ID = "uci_597_1182"


class History:
    def __init__(self, directory):
        path = directory / "garments_worker_productivity.csv"
        self.snapshot = json.loads((directory / "uci_holdout_predictions.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != self.snapshot["dataset_sha256"]:
            raise ValueError("CSV berbeda dari sumber prediksi. Ekstrak ulang pasangan file data dari ZIP.")
        with path.open(encoding="utf-8-sig", newline="") as f:
            self.records = {}
            for i, raw in enumerate(csv.DictReader(f), 1):
                identifier = f"uci_597_{i:04d}"
                self.records[identifier] = normalize_uci_row(raw, identifier)

    def select(self, args):
        if len(args) == 1 and args[0] in self.records:
            return self.records[args[0]]
        if len(args) != 3:
            raise ValueError("Gunakan /pilih ID atau /pilih YYYY-MM-DD nomor_tim departemen.")
        date, team, dept = parse_uci_date(args[0]).isoformat(), int(args[1]), normalize_department(args[2]).value
        matches = [r for r in self.records.values() if (r["production_date"], r["team_id"], r["department"]) == (date, team, dept)]
        if len(matches) != 1:
            ids = ", ".join(r["source_record_id"] for r in matches)
            raise ValueError(f"Pilih salah satu ID: {ids}" if ids else "Kombinasi tanggal, tim dan departemen tidak ditemukan.")
        return matches[0]


def respond(history, row, topics, session):
    date, team, dept = row["production_date"], row["team_id"], row["department"]
    label = f"Tim {team} {dept}, {date}"
    source = row["source_record_id"]
    actual, target = row["actual_productivity"], row["target_productivity"]
    snap = history.snapshot
    version = snap["model_version"]
    predicted = snap["predictions"].get(source)
    answer, evidence = [], []
    status = "answered"
    if "unsupported" in topics or "individual" in topics:
        return ChatResponse(conversation_id=session, answer="Pilih catatan tim dengan /pilih. Tanyakan aktual, target, prediksi atau rata-rata tim terpilih.", status="insufficient_data")
    if "target" in topics or "actual" in topics:
        gap, comparison = get_target_comparison(actual, target)
        outcome = "di bawah target" if comparison.value == "below_target" else "mencapai target"
        answer.append(f"{label}. Aktual UCI {actual:.2%}, target {target:.2%}. Hasilnya {outcome} ({gap:+.2f} poin persentase).")
        evidence.append(EvidenceRef(type="historical_summary", id=source))
    if "target" in topics:
        if predicted is None:
            answer.append("Estimasi tersimpan hanya tersedia untuk periode uji 2–11 Maret 2015.")
            status = "insufficient_data"
        else:
            gap, _ = get_target_comparison(predicted, target)
            answer.append(f"Estimasi ulang {version} dari input sebelum shift: {predicted:.2%} ({gap:+.2f} poin persentase terhadap target).")
            evidence.append(EvidenceRef(type="prediction", id=f"replay:{snap['model_sha256'][:12]}:{source}"))
    if "history" in topics:
        records = [r for r in history.records.values() if r["team_id"] == team and r["department"] == dept and r["production_date"] <= date]
        avg = mean(r["actual_productivity"] for r in records)
        answer.append(f"Rata-rata aktual Tim {team} {dept} sampai {date} (inklusif): {avg:.2%} dari {len(records)} catatan.")
        evidence.append(EvidenceRef(type="historical_summary", id=f"uci_597:{team}:{dept}:through:{date}"))
    if "model" in topics:
        answer.append(f"Model snapshot {version}, periode uji {' s.d. '.join(snap['test_date_range'])}.")
        evidence.append(EvidenceRef(type="model_info", id=f"{version}:{snap['model_sha256'][:12]}"))
    if "cause" in topics:
        answer.append("Catatan observasi belum membuktikan penyebab selisih.")
        if len(topics) == 1:
            status = "insufficient_data"
    return ChatResponse(conversation_id=session, answer=" ".join(answer), evidence=evidence, status=status)


def main():
    load_dotenv(ROOT / ".env")
    history = History(ROOT / "data")
    row = history.records[DEFAULT_ID]
    session = str(uuid4())
    print(f"ProdPulse | UCI 597: {len(history.records)} catatan | {len(history.snapshot['predictions'])} estimasi holdout")
    print("Perintah: /data, /rekap, /pilih YYYY-MM-DD nomor_tim departemen, /pilih ID, /exit")
    while True:
        try:
            scope = f"{row['production_date']} Tim {row['team_id']} {row['department']}" if row else "pilih catatan"
            message = input(f"[{scope}] Lu > ").strip()
            if message == "/exit":
                break
            if message.split()[:1] == ["/pilih"]:
                row = None
                row = history.select(message.split()[1:])
                continue
            if row is None:
                print("Pilih catatan dulu dengan /pilih.")
                continue
            if not 1 <= len(message) <= 2000:
                print("Isi pesan 1–2000 karakter.")
                continue
            if message == "/data":
                topics = ["actual", "target"]
            elif message == "/rekap":
                topics = ["history"]
            else:
                topics = select_topics(f"Konteks pilihan: {scope}. Pertanyaan tentang data tercatat pilih actual. "
                                       "Jika meminta filter tanggal/tim/departemen berbeda pilih unsupported. "
                                       "history hanya untuk rata-rata tim ini sejak awal data sampai tanggal terpilih. "
                                       f"Pertanyaan pengguna: {message}")
            print(respond(history, row, topics, session).model_dump_json(indent=2))
        except (EOFError, KeyboardInterrupt):
            break
        except (ValueError, ProviderUnavailable) as error:
            print(error)


if __name__ == "__main__":
    main()
