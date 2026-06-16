from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import pandas as pd

from .models import FinancialMetrics, StockMeta
from .utils import first_existing, to_float


def _import_akshare():
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("AkShare is not installed. Run: python -m pip install -r requirements.txt") from exc
    return ak


def _normalize_code(code: object) -> str:
    text = str(code).strip()
    return text.zfill(6) if text.isdigit() else text


def is_non_st_name(name: str) -> bool:
    upper = name.upper()
    bad_markers = ["ST", "*ST", "退", "退市"]
    return not any(marker in upper for marker in bad_markers)


def load_a_share_universe(limit: int | None = None) -> list[StockMeta]:
    ak = _import_akshare()
    try:
        spot = ak.stock_zh_a_spot_em()
    except Exception as exc:
        raise RuntimeError(
            "Failed to load A-share universe from AkShare/Eastmoney. "
            "Check outbound network access, proxy settings, or try again later."
        ) from exc
    stocks: list[StockMeta] = []
    for _, row in spot.iterrows():
        code = _normalize_code(first_existing(row, ["代码", "code", "symbol"]))
        name = str(first_existing(row, ["名称", "name"]) or "").strip()
        if not code or not name or not is_non_st_name(name):
            continue
        stocks.append(
            StockMeta(
                code=code,
                name=name,
                market=str(first_existing(row, ["市场", "market"]) or ""),
                pe=to_float(first_existing(row, ["市盈率-动态", "市盈率", "pe"])),
                pb=to_float(first_existing(row, ["市净率", "pb"])),
                turnover_rate=to_float(first_existing(row, ["换手率", "turnover"])),
            )
        )
        if limit and len(stocks) >= limit:
            break
    return stocks


def load_daily_bars(code: str, lookback_calendar_days: int = 45) -> pd.DataFrame:
    ak = _import_akshare()
    end = date.today()
    start = end - timedelta(days=lookback_calendar_days)
    raw = ak.stock_zh_a_hist(
        symbol=code,
        period="daily",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        adjust="qfq",
    )
    return normalize_bars(raw)


def normalize_bars(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["date", "open", "close", "high", "low", "volume", "amount"])
    mapping = {
        "日期": "date",
        "date": "date",
        "开盘": "open",
        "open": "open",
        "收盘": "close",
        "close": "close",
        "最高": "high",
        "high": "high",
        "最低": "low",
        "low": "low",
        "成交量": "volume",
        "volume": "volume",
        "成交额": "amount",
        "amount": "amount",
    }
    bars = raw.rename(columns={col: mapping[col] for col in raw.columns if col in mapping}).copy()
    needed = ["date", "open", "close", "high", "low", "volume"]
    missing = [col for col in needed if col not in bars.columns]
    if missing:
        raise ValueError(f"Daily bar data missing columns: {missing}")
    for col in ["open", "close", "high", "low", "volume", "amount"]:
        if col in bars.columns:
            bars[col] = pd.to_numeric(bars[col], errors="coerce")
    bars["date"] = pd.to_datetime(bars["date"]).dt.strftime("%Y-%m-%d")
    return bars.dropna(subset=["open", "close", "high", "low", "volume"]).sort_values("date").reset_index(drop=True)


def load_financial_metrics(code: str) -> FinancialMetrics:
    ak = _import_akshare()
    parsers = [
        lambda: _parse_financial_analysis_indicator(ak.stock_financial_analysis_indicator(symbol=code)),
        lambda: _parse_financial_abstract(ak.stock_financial_abstract_ths(symbol=code)),
    ]
    for parser in parsers:
        try:
            metrics = parser()
        except Exception:
            continue
        if any(value is not None for value in (metrics.roe, metrics.net_profit_growth, metrics.revenue_growth)):
            return metrics
    return FinancialMetrics()


def _latest_value_by_keywords(df: pd.DataFrame, keywords: Iterable[str]) -> float | None:
    if df is None or df.empty:
        return None
    keyword_list = list(keywords)
    text_cols = [col for col in df.columns if df[col].dtype == object]
    for _, row in df.iterrows():
        haystack = " ".join(str(row[col]) for col in text_cols)
        if any(keyword in haystack for keyword in keyword_list):
            for value in reversed(list(row.values)):
                parsed = to_float(value)
                if parsed is not None:
                    return parsed
    return None


def _latest_column_by_keywords(df: pd.DataFrame, keywords: Iterable[str]) -> float | None:
    if df is None or df.empty:
        return None
    for col in df.columns:
        if any(keyword in str(col) for keyword in keywords):
            for value in df[col].dropna().tolist():
                parsed = to_float(value)
                if parsed is not None:
                    return parsed
    return None


def _parse_financial_analysis_indicator(df: pd.DataFrame) -> FinancialMetrics:
    return FinancialMetrics(
        roe=_latest_column_by_keywords(df, ["净资产收益率", "ROE"])
        or _latest_value_by_keywords(df, ["净资产收益率", "ROE"]),
        net_profit_growth=_latest_column_by_keywords(df, ["净利润增长率", "净利润同比", "净利润同比增长"])
        or _latest_value_by_keywords(df, ["净利润增长率", "净利润同比", "净利润同比增长"]),
        revenue_growth=_latest_column_by_keywords(df, ["主营业务收入增长率", "营业收入增长率", "营收同比"])
        or _latest_value_by_keywords(df, ["主营业务收入增长率", "营业收入增长率", "营收同比"]),
    )


def _parse_financial_abstract(df: pd.DataFrame) -> FinancialMetrics:
    return FinancialMetrics(
        roe=_latest_column_by_keywords(df, ["净资产收益率", "ROE"])
        or _latest_value_by_keywords(df, ["净资产收益率", "ROE"]),
        net_profit_growth=_latest_column_by_keywords(df, ["归母净利润同比", "净利润同比", "净利润增长"])
        or _latest_value_by_keywords(df, ["归母净利润同比", "净利润同比", "净利润增长"]),
        revenue_growth=_latest_column_by_keywords(df, ["营业总收入同比", "营业收入同比", "营收增长"])
        or _latest_value_by_keywords(df, ["营业总收入同比", "营业收入同比", "营收增长"]),
    )
