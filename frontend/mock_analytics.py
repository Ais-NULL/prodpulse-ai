"""Deterministic historical samples for the explicitly labeled frontend demo."""

from datetime import date
from statistics import mean

MONTHLY_BASE = (.53, .56, .71, .60, .66, .59, .81, .65, .72, .62, .76, .84)
TEAM_OFFSETS = (-.26, -.14, -.11, -.18, .02, .04, .2, .16, -.22, .12, -.04, .06)
MONTH_LABELS = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")
SAMPLE_ROWS = tuple(
    (date(2025, month, 1), team_id, base + offset)
    for month, base in enumerate(MONTHLY_BASE, start=1)
    for team_id, offset in enumerate(TEAM_OFFSETS, start=1)
)


def historical_trend() -> list[tuple[str, float]]:
    return [
        (label, mean(value for month, _, value in SAMPLE_ROWS if month.month == month_number))
        for month_number, label in enumerate(MONTH_LABELS, start=1)
    ]


def team_productivity() -> list[tuple[str, float]]:
    return [
        (f"Tim {team_number:02}", mean(value for _, team, value in SAMPLE_ROWS if team == team_number))
        for team_number in range(1, len(TEAM_OFFSETS) + 1)
    ]
