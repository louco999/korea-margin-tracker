"""End-to-end update: fetch KOFIA → merge CSV → chart → refresh README."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from .chart import plot_history
from .fetch_kofia import fetch_recent
from .storage import load_history, merge_points, save_history

ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = ROOT / "data" / "margin_balance.csv"
LATEST_JSON = ROOT / "data" / "latest.json"
CHART_PNG = ROOT / "charts" / "margin_balance.png"
README = ROOT / "README.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("update")


def _fmt(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "n/a"
    return f"{v:.{digits}f}"


def update_readme(snapshot: dict) -> None:
    if not README.exists():
        logger.warning("README.md missing; skip badge section update")
        return

    text = README.read_text(encoding="utf-8")
    as_of = snapshot["as_of"]
    margin = snapshot["margin_loan"]
    delta = snapshot.get("margin_loan_change")
    deposit = snapshot.get("investor_deposit")
    credit_total = snapshot.get("credit_total")
    fetched = snapshot.get("fetched_at", "")

    delta_s = "n/a" if delta is None else f"{delta:+.2f}"
    status = (
        f"| Field | Value |\n"
        f"|---|---|\n"
        f"| **As of** | `{as_of}` |\n"
        f"| **Margin loan (신용거래융자)** | **{_fmt(margin)} trillion KRW** |\n"
        f"| **Day change** | `{delta_s}` trillion KRW |\n"
        f"| **Securities-backed loan** | {_fmt(snapshot.get('securities_backed_loan'))} T |\n"
        f"| **Credit total** | {_fmt(credit_total)} T |\n"
        f"| **Investor deposits** | {_fmt(deposit)} T |\n"
        f"| **Fetched at (UTC)** | `{fetched}` |\n"
    )

    block = f"<!-- LATEST:START -->\n{status}<!-- LATEST:END -->"
    if "<!-- LATEST:START -->" in text and "<!-- LATEST:END -->" in text:
        text = re.sub(
            r"<!-- LATEST:START -->.*?<!-- LATEST:END -->",
            block,
            text,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n## Latest snapshot\n\n" + block + "\n"

    # bump chart cache-buster so GitHub UI refreshes the image
    text = re.sub(
        r"(charts/margin_balance\.png)(\?v=[0-9a-f]+)?",
        rf"\1?v={as_of.replace('-', '')}",
        text,
    )
    README.write_text(text, encoding="utf-8")
    logger.info("README latest section updated")


def run(skip_fetch: bool = False) -> int:
    history = load_history(DATA_CSV)

    if not skip_fetch:
        points = fetch_recent()
        history = merge_points(history, points, source="kofia_api")
        save_history(DATA_CSV, history)
        latest = points[-1]
        prev = points[-2] if len(points) >= 2 else None
        margin = latest.values["margin_loan"]
        snapshot = {
            "as_of": latest.date,
            "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "unit": "trillion_KRW",
            "margin_loan": margin,
            "margin_loan_change": None
            if prev is None
            else round(margin - prev.values["margin_loan"], 6),
            "short_sale": latest.values.get("short_sale"),
            "securities_backed_loan": latest.values.get("securities_backed_loan"),
            "credit_total": latest.values.get("credit_total"),
            "investor_deposit": latest.values.get("investor_deposit"),
            "source": "KOFIA FreeSIS STATSCUSUBMAIN01",
            "source_url": "https://freesis.kofia.or.kr/",
            "recent_days": [{"date": p.date, **p.values} for p in points],
        }
    else:
        # offline: rebuild snapshot from CSV tail
        if not history:
            logger.error("No history and skip_fetch set")
            return 1
        last_date = sorted(history)[-1]
        row = history[last_date]
        prev_date = sorted(history)[-2] if len(history) >= 2 else None
        margin = float(row["margin_loan"])
        delta = None
        if prev_date:
            delta = round(margin - float(history[prev_date]["margin_loan"]), 6)
        snapshot = {
            "as_of": last_date,
            "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "unit": "trillion_KRW",
            "margin_loan": margin,
            "margin_loan_change": delta,
            "short_sale": float(row["short_sale"]) if row.get("short_sale") else None,
            "securities_backed_loan": float(row["securities_backed_loan"])
            if row.get("securities_backed_loan")
            else None,
            "credit_total": float(row["credit_total"]) if row.get("credit_total") else None,
            "investor_deposit": float(row["investor_deposit"])
            if row.get("investor_deposit")
            else None,
            "source": row.get("source", "csv"),
            "source_url": "https://freesis.kofia.or.kr/",
        }

    LATEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    LATEST_JSON.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    plot_history(DATA_CSV, CHART_PNG)
    update_readme(snapshot)

    logger.info(
        "Done. as_of=%s margin_loan=%sT csv_rows=%d",
        snapshot["as_of"],
        snapshot["margin_loan"],
        len(history),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update Korea margin tracker data")
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Only rebuild chart/README from existing CSV",
    )
    args = parser.parse_args(argv)
    try:
        return run(skip_fetch=args.skip_fetch)
    except Exception:
        logger.exception("Update failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
