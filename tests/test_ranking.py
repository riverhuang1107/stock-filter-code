from stock_filter_tool.models import FinancialMetrics, Signal, StockMeta
from stock_filter_tool.ranking import score_candidate


def test_financials_can_be_missing():
    candidate = score_candidate(
        StockMeta(code="000001", name="平安银行"),
        Signal(
            signal_date="2026-06-12",
            previous_date="2026-06-11",
            body_ratio=2.0,
            body_pct=4.0,
            close_position=0.8,
            volume_ratio=1.8,
        ),
        FinancialMetrics(),
    )
    assert candidate.score > 0
    assert "大阳包小阴" in candidate.reason
