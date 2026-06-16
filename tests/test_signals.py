import pandas as pd

from stock_filter_tool.signals import find_bullish_engulfing_signal


def test_bullish_engulfing_signal_matches():
    bars = pd.DataFrame(
        [
            {"date": "2026-06-10", "open": 10.0, "close": 10.2, "high": 10.3, "low": 9.9, "volume": 1000},
            {"date": "2026-06-11", "open": 10.3, "close": 10.15, "high": 10.35, "low": 10.1, "volume": 900},
            {"date": "2026-06-12", "open": 10.1, "close": 10.72, "high": 10.8, "low": 10.0, "volume": 2500},
        ]
    )
    signal = find_bullish_engulfing_signal(bars, days=3)
    assert signal is not None
    assert signal.signal_date == "2026-06-12"
    assert signal.body_ratio >= 1.5


def test_bullish_engulfing_signal_rejects_non_engulfing():
    bars = pd.DataFrame(
        [
            {"date": "2026-06-10", "open": 10.0, "close": 10.2, "high": 10.3, "low": 9.9, "volume": 1000},
            {"date": "2026-06-11", "open": 10.3, "close": 10.15, "high": 10.35, "low": 10.1, "volume": 900},
            {"date": "2026-06-12", "open": 10.2, "close": 10.45, "high": 10.5, "low": 10.1, "volume": 2500},
        ]
    )
    assert find_bullish_engulfing_signal(bars, days=3) is None
