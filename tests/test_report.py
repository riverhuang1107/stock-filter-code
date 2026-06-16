from pathlib import Path

from stock_filter_tool.models import FinancialMetrics, Signal, StockCandidate, StockMeta
from stock_filter_tool.report import render_html, render_markdown


def _candidate(tmp_path: Path) -> StockCandidate:
    chart = tmp_path / "000001.png"
    chart.write_bytes(b"fake-png")
    return StockCandidate(
        meta=StockMeta(code="000001", name="平安银行"),
        signal=Signal("2026-06-12", "2026-06-11", 2.0, 4.0, 0.8, 1.8),
        financials=FinancialMetrics(roe=12.0, net_profit_growth=18.0, revenue_growth=9.0),
        score=88.0,
        technical_score=90.0,
        volume_score=72.0,
        financial_score=84.0,
        reason="测试原因",
        chart_path=chart,
    )


def test_report_contains_chart(tmp_path):
    candidate = _candidate(tmp_path)
    html = render_html([candidate])
    markdown = render_markdown([candidate])
    assert "data:image/png;base64" in html
    assert "000001.png" in markdown
