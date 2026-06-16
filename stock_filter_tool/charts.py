from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "stock-filter-matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from .models import Signal, StockMeta


def create_kline_chart(
    bars: pd.DataFrame,
    meta: StockMeta,
    signal: Signal,
    output_dir: Path,
    chart_days: int = 5,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_bars = bars.sort_values("date").tail(chart_days).copy()
    chart_bars["date_dt"] = pd.to_datetime(chart_bars["date"])
    path = output_dir / f"{meta.code}.png"
    fig, (ax_price, ax_volume) = plt.subplots(
        2,
        1,
        figsize=(9, 5.5),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    width = 0.6
    dates = mdates.date2num(chart_bars["date_dt"])
    for x, (_, row) in zip(dates, chart_bars.iterrows()):
        color = "#d62728" if row["close"] >= row["open"] else "#2ca02c"
        ax_price.vlines(x, row["low"], row["high"], color=color, linewidth=1.2)
        body_low = min(row["open"], row["close"])
        body_height = abs(row["close"] - row["open"]) or 0.01
        ax_price.add_patch(
            plt.Rectangle(
                (x - width / 2, body_low),
                width,
                body_height,
                facecolor=color,
                edgecolor=color,
                alpha=0.85,
            )
        )
        ax_volume.bar(x, row["volume"], width=width, color=color, alpha=0.45)
        if str(row["date"]) == signal.signal_date:
            ax_price.annotate(
                "signal",
                xy=(x, row["high"]),
                xytext=(0, 16),
                textcoords="offset points",
                ha="center",
                color="#1f77b4",
                arrowprops={"arrowstyle": "->", "color": "#1f77b4"},
            )
    ax_price.set_title(f"{meta.code} - last {len(chart_bars)} trading days")
    ax_price.set_ylabel("Price")
    ax_volume.set_ylabel("Volume")
    ax_volume.xaxis_date()
    ax_volume.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax_price.grid(alpha=0.25)
    ax_volume.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
