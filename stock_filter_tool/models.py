from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class StockMeta:
    code: str
    name: str
    market: str = ""
    pe: Optional[float] = None
    pb: Optional[float] = None
    turnover_rate: Optional[float] = None


@dataclass(frozen=True)
class Signal:
    signal_date: str
    previous_date: str
    body_ratio: float
    body_pct: float
    close_position: float
    volume_ratio: float


@dataclass(frozen=True)
class FinancialMetrics:
    roe: Optional[float] = None
    net_profit_growth: Optional[float] = None
    revenue_growth: Optional[float] = None


@dataclass
class StockCandidate:
    meta: StockMeta
    signal: Signal
    financials: FinancialMetrics
    score: float
    technical_score: float
    volume_score: float
    financial_score: float
    reason: str
    chart_path: Optional[Path] = None
