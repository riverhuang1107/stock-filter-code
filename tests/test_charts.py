from pathlib import Path

import pandas as pd

from stock_filter_tool.charts import create_kline_chart
from stock_filter_tool.models import Signal, StockMeta


def test_chart_png_is_created(tmp_path: Path):
    bars = pd.DataFrame(
        [
            {"date": "2026-06-08", "open": 10.0, "close": 10.1, "high": 10.2, "low": 9.9, "volume": 1000},
            {"date": "2026-06-09", "open": 10.1, "close": 10.0, "high": 10.2, "low": 9.9, "volume": 950},
            {"date": "2026-06-10", "open": 10.0, "close": 10.2, "high": 10.3, "low": 9.9, "volume": 1100},
            {"date": "2026-06-11", "open": 10.3, "close": 10.15, "high": 10.35, "low": 10.1, "volume": 900},
            {"date": "2026-06-12", "open": 10.1, "close": 10.72, "high": 10.8, "low": 10.0, "volume": 2500},
        ]
    )
    path = create_kline_chart(
        bars,
        StockMeta(code="000001", name="平安银行"),
        Signal("2026-06-12", "2026-06-11", 2.0, 4.0, 0.8, 1.8),
        tmp_path,
        chart_days=5,
    )
    assert path.exists()
    assert path.stat().st_size > 0
