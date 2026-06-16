from __future__ import annotations

import pandas as pd

from .models import Signal


def find_bullish_engulfing_signal(bars: pd.DataFrame, days: int = 3) -> Signal | None:
    if bars is None or len(bars) < 2:
        return None
    bars = bars.sort_values("date").reset_index(drop=True)
    start_idx = max(1, len(bars) - days)
    for idx in range(len(bars) - 1, start_idx - 1, -1):
        signal = _detect_at(bars, idx)
        if signal:
            return signal
    return None


def _detect_at(bars: pd.DataFrame, idx: int) -> Signal | None:
    prev = bars.iloc[idx - 1]
    cur = bars.iloc[idx]
    prev_body = abs(prev["close"] - prev["open"])
    cur_body = abs(cur["close"] - cur["open"])
    prev_ref = max(float(prev["close"]), 0.01)
    cur_ref = max(float(cur["open"]), 0.01)
    prev_is_small_yin = prev["close"] < prev["open"] and prev_body / prev_ref <= 0.025
    cur_is_big_yang = cur["close"] > cur["open"] and cur_body / cur_ref >= 0.03
    body_engulfs = cur["open"] <= prev["close"] and cur["close"] >= prev["open"]
    range_engulfs = cur["low"] <= prev["low"] and cur["high"] >= prev["high"]
    body_ratio = cur_body / max(prev_body, 0.01)
    high_low = max(float(cur["high"] - cur["low"]), 0.01)
    close_position = (cur["close"] - cur["low"]) / high_low
    if not (
        prev_is_small_yin
        and cur_is_big_yang
        and body_engulfs
        and range_engulfs
        and body_ratio >= 1.5
        and close_position >= 0.65
    ):
        return None
    history = bars.iloc[max(0, idx - 5):idx]
    avg_volume = float(history["volume"].mean()) if not history.empty else float(cur["volume"])
    volume_ratio = float(cur["volume"]) / max(avg_volume, 1.0)
    return Signal(
        signal_date=str(cur["date"]),
        previous_date=str(prev["date"]),
        body_ratio=round(float(body_ratio), 2),
        body_pct=round(float(cur_body / cur_ref * 100), 2),
        close_position=round(float(close_position), 2),
        volume_ratio=round(volume_ratio, 2),
    )
