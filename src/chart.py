"""Generate margin-balance time-series chart."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def plot_history(csv_path: Path, out_path: Path, title: str | None = None) -> Path:
    dates: list[datetime] = []
    values: list[float] = []

    with csv_path.open(encoding="utf-8") as f:
        # lightweight parse without pandas
        header = f.readline().strip().split(",")
        idx_date = header.index("date")
        idx_ml = header.index("margin_loan")
        for line in f:
            parts = line.strip().split(",")
            if len(parts) <= max(idx_date, idx_ml):
                continue
            raw = parts[idx_ml].strip()
            if not raw:
                continue
            dates.append(datetime.strptime(parts[idx_date], "%Y-%m-%d"))
            values.append(float(raw))

    if not dates:
        raise RuntimeError(f"No data to chart in {csv_path}")

    plt.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(12, 6.2), dpi=150)
    fig.patch.set_facecolor("#0f1419")
    ax.set_facecolor("#0f1419")

    peak_i = values.index(max(values))
    ax.plot(dates, values, color="#3d9eff", linewidth=2.2, zorder=3)
    ax.fill_between(dates, values, alpha=0.15, color="#3d9eff")
    ax.scatter(
        [dates[peak_i]],
        [values[peak_i]],
        color="#ffd166",
        s=45,
        zorder=4,
        edgecolors="white",
        linewidths=0.5,
    )
    ax.scatter(
        [dates[-1]],
        [values[-1]],
        color="#ff6b6b",
        s=40,
        zorder=4,
        edgecolors="white",
        linewidths=0.5,
    )

    ax.axhline(values[peak_i], color="#ffd166", linestyle="--", linewidth=0.8, alpha=0.45)
    ax.annotate(
        f"Peak {values[peak_i]:.2f}\n{dates[peak_i]:%Y-%m-%d}",
        xy=(dates[peak_i], values[peak_i]),
        xytext=(0, 14),
        textcoords="offset points",
        ha="center",
        color="#ffd166",
        fontsize=8.5,
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#1a2332",
            edgecolor="#ffd166",
            alpha=0.9,
        ),
    )
    ax.annotate(
        f"Latest {values[-1]:.2f}\n{dates[-1]:%Y-%m-%d}",
        xy=(dates[-1], values[-1]),
        xytext=(-10, -28),
        textcoords="offset points",
        ha="right",
        color="#ff6b6b",
        fontsize=8.5,
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#1a2332",
            edgecolor="#ff6b6b",
            alpha=0.9,
        ),
    )

    peak = max(values)
    latest = values[-1]
    change = (latest / peak - 1.0) * 100 if peak else 0.0
    box = (
        f"Peak: {peak:.2f}T KRW\n"
        f"Latest: {latest:.2f}T KRW\n"
        f"From peak: {change:+.1f}%\n"
        f"Points: {len(values)}"
    )
    ax.text(
        0.02,
        0.98,
        box,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        color="#e8eef5",
        bbox=dict(
            boxstyle="round,pad=0.5",
            facecolor="#1a2332",
            edgecolor="#3d4f66",
            alpha=0.95,
        ),
    )

    ax.set_title(
        title
        or "Korea Margin Loan Balance (신용거래융자)\nSource: KOFIA FreeSIS",
        color="white",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.set_ylabel("Trillion KRW", color="#c5d0de")
    ax.set_xlabel("Date", color="#c5d0de")
    ax.tick_params(colors="#9aa8b8", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#2a3544")
    ax.grid(True, color="#1f2a38", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    ax.text(
        0.99,
        0.01,
        "Unit: trillion KRW | Auto-updated from KOFIA FreeSIS",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
        color="#6b7a8d",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return out_path
