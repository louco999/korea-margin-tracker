"""CSV history storage for Korea margin series."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .fetch_kofia import SeriesPoint

# Stable column order for git-friendly diffs
COLUMNS = [
    "date",
    "margin_loan",
    "short_sale",
    "securities_backed_loan",
    "credit_total",
    "investor_deposit",
    "source",
]


def load_history(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get("date") or "").strip()
            if date:
                rows[date] = row
    return rows


def merge_points(
    existing: dict[str, dict[str, str]],
    points: Iterable[SeriesPoint],
    source: str = "kofia_api",
) -> dict[str, dict[str, str]]:
    """
    Merge API points into history.

    Live API values overwrite the same date (authoritative).
    Seed/manual rows for dates not returned by the API are kept.
    """
    out = dict(existing)
    for p in points:
        row = out.get(p.date, {"date": p.date})
        row["date"] = p.date
        row["source"] = source
        for col in COLUMNS[1:-1]:
            if col in p.values and p.values[col] is not None:
                row[col] = f"{p.values[col]:.6f}".rstrip("0").rstrip(".")
        out[p.date] = row
    return out


def save_history(path: Path, rows: dict[str, dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [rows[d] for d in sorted(rows)]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in ordered:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})
