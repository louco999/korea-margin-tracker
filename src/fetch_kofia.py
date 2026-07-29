"""Fetch Korea stock-market credit/margin balances from KOFIA FreeSIS."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Public FreeSIS endpoint used by the 증시자금/신용공여 dashboard.
# Returns ~15 recent trading days per request (million KRW).
KOFIA_URL = "https://freesis.kofia.or.kr/stockSubMain/STATSCUSUBMAIN01BO.do"
USER_AGENT = (
    "korea-margin-tracker/1.0 "
    "(+https://github.com/louco999/korea-margin-tracker; research use)"
)

# Rows we care about: (category, item) -> field name in CSV/JSON
METRICS = {
    ("신용공여", "신용거래융자"): "margin_loan",  # main leverage gauge
    ("신용공여", "신용거래대주"): "short_sale",
    ("신용공여", "예탁증권담보융자"): "securities_backed_loan",
    ("신용공여", "합계"): "credit_total",
    ("증시자금", "투자자예탁금"): "investor_deposit",
}


@dataclass(frozen=True)
class SeriesPoint:
    date: str  # YYYY-MM-DD
    values: dict[str, float]  # metric -> trillion KRW


def _post_json(url: str, payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=body,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    if not data.get("success", True) and data.get("code") not in (None, "SUCCESS"):
        raise RuntimeError(f"KOFIA API error: {data.get('message') or data}")
    return data


def _parse_date(yyyymmdd: str) -> str:
    return datetime.strptime(yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")


def fetch_recent() -> list[SeriesPoint]:
    """
    Pull the latest ~15 trading days of margin / market-fund series.

    Values are converted from million KRW (API unit) to trillion KRW.
    """
    payload = {
        "userId": "GUEST",
        "serviceId": "STATSCUSUBMAIN01",
        "tmpV87": "1",  # absolute change mode (matches UI default)
    }
    try:
        data = _post_json(KOFIA_URL, payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to fetch KOFIA data: {exc}") from exc

    title = data.get("dmTitle") or {}
    rows = data.get("dsResultList") or []
    if not title or not rows:
        raise RuntimeError("KOFIA response missing dmTitle/dsResultList")

    # TMPV6..TMPV20 are date columns (newest first)
    date_keys = [f"TMPV{i}" for i in range(6, 21) if title.get(f"TMPV{i}")]
    dates = [_parse_date(str(title[k])) for k in date_keys]

    # Accumulate per-date metric dicts
    by_date: dict[str, dict[str, float]] = {d: {} for d in dates}

    for row in rows:
        key = (row.get("TMPV1"), row.get("TMPV2"))
        metric = METRICS.get(key)
        if not metric:
            continue
        for date_key, date in zip(date_keys, dates):
            raw = row.get(date_key)
            if raw is None or raw == "":
                continue
            # API unit: million KRW → trillion KRW
            by_date[date][metric] = round(float(raw) / 1_000_000.0, 6)

    points: list[SeriesPoint] = []
    for date in sorted(by_date):
        vals = by_date[date]
        if "margin_loan" not in vals:
            continue
        points.append(SeriesPoint(date=date, values=vals))

    if not points:
        raise RuntimeError("No margin_loan points parsed from KOFIA response")

    logger.info(
        "Fetched %d trading days (%s → %s), latest margin_loan=%.4fT",
        len(points),
        points[0].date,
        points[-1].date,
        points[-1].values["margin_loan"],
    )
    return points


def fetch_latest_snapshot() -> dict[str, Any]:
    """Return a compact JSON-serializable snapshot of the newest observation."""
    points = fetch_recent()
    latest = points[-1]
    prev = points[-2] if len(points) >= 2 else None
    margin = latest.values["margin_loan"]
    delta = None if prev is None else round(margin - prev.values["margin_loan"], 6)
    return {
        "as_of": latest.date,
        "fetched_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unit": "trillion_KRW",
        "margin_loan": margin,
        "margin_loan_change": delta,
        "short_sale": latest.values.get("short_sale"),
        "securities_backed_loan": latest.values.get("securities_backed_loan"),
        "credit_total": latest.values.get("credit_total"),
        "investor_deposit": latest.values.get("investor_deposit"),
        "source": "KOFIA FreeSIS STATSCUSUBMAIN01",
        "source_url": "https://freesis.kofia.or.kr/",
        "recent_days": [
            {"date": p.date, **p.values} for p in points
        ],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    snap = fetch_latest_snapshot()
    print(json.dumps(snap, ensure_ascii=False, indent=2))
