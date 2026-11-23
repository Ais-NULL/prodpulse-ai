"""Display units and labels shared by the frontend pages."""

from shared.contracts import Department, PredictionResponse, TargetStatus

FIELD_LABELS = {
    "production_date": "Tanggal produksi",
    "department": "Departemen",
    "team_id": "ID tim",
    "target_productivity": "Target produktivitas (%)",
    "smv_minutes": "Standard Minute Value (menit)",
    "worker_count": "Jumlah pekerja ekuivalen",
    "message": "Pesan",
}
DEPARTMENT_LABELS = {Department.SEWING: "Sewing", Department.FINISHING: "Finishing"}
TARGET_LABELS = {
    TargetStatus.BELOW_TARGET: "Di bawah target",
    TargetStatus.MEETS_OR_EXCEEDS: "Memenuhi atau melampaui target",
}


def prediction_context(result: PredictionResponse) -> str:
    department = DEPARTMENT_LABELS[result.department]
    return f"{department} · Tim {result.team_id} · {result.production_date:%d/%m/%Y}"


def format_ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def format_gap(value: float) -> str:
    if value == 0:
        return "0.0 pp"
    return f"{value:+.1f} pp"


def format_count(value: int | None) -> str:
    return "—" if value is None else f"{value:,}".replace(",", ".")
