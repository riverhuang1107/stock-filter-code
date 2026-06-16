from __future__ import annotations

from .models import FinancialMetrics, Signal, StockCandidate, StockMeta
from .utils import clamp


def score_candidate(meta: StockMeta, signal: Signal, financials: FinancialMetrics) -> StockCandidate:
    technical_score = _technical_score(signal)
    volume_score = clamp(signal.volume_ratio / 2.5 * 100)
    financial_score = _financial_score(financials)
    total = round(technical_score * 0.40 + volume_score * 0.25 + financial_score * 0.35, 2)
    reason = build_reason(signal, financials, technical_score, volume_score, financial_score)
    return StockCandidate(
        meta=meta,
        signal=signal,
        financials=financials,
        score=total,
        technical_score=round(technical_score, 2),
        volume_score=round(volume_score, 2),
        financial_score=round(financial_score, 2),
        reason=reason,
    )


def _technical_score(signal: Signal) -> float:
    body_ratio_score = clamp(signal.body_ratio / 3.0 * 100)
    body_pct_score = clamp(signal.body_pct / 6.0 * 100)
    close_position_score = clamp(signal.close_position * 100)
    return body_ratio_score * 0.35 + body_pct_score * 0.40 + close_position_score * 0.25


def _financial_score(financials: FinancialMetrics) -> float:
    parts: list[tuple[float, float]] = []
    if financials.roe is not None:
        parts.append((clamp(financials.roe / 20.0 * 100), 0.4))
    if financials.net_profit_growth is not None:
        parts.append((clamp((financials.net_profit_growth + 20.0) / 70.0 * 100), 0.3))
    if financials.revenue_growth is not None:
        parts.append((clamp((financials.revenue_growth + 10.0) / 50.0 * 100), 0.3))
    if not parts:
        return 45.0
    weighted = sum(score * weight for score, weight in parts)
    weight_sum = sum(weight for _, weight in parts)
    completeness_bonus = 10.0 * min(weight_sum, 1.0)
    return clamp(weighted / weight_sum + completeness_bonus)


def build_reason(
    signal: Signal,
    financials: FinancialMetrics,
    technical_score: float,
    volume_score: float,
    financial_score: float,
) -> str:
    metrics = [
        f"{signal.signal_date} 出现大阳包小阴",
        f"阳线实体为前一日实体 {signal.body_ratio:.2f} 倍",
        f"成交量为近 5 日均量 {signal.volume_ratio:.2f} 倍",
    ]
    if financials.roe is not None:
        metrics.append(f"ROE {financials.roe:.2f}%")
    if financials.net_profit_growth is not None:
        metrics.append(f"净利润增长 {financials.net_profit_growth:.2f}%")
    if financials.revenue_growth is not None:
        metrics.append(f"营收增长 {financials.revenue_growth:.2f}%")
    metrics.append(f"技术/量能/业绩评分 {technical_score:.1f}/{volume_score:.1f}/{financial_score:.1f}")
    return "；".join(metrics)
