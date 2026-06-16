from __future__ import annotations

from datetime import date, timedelta
import json
import time
from typing import Iterable

import pandas as pd
import requests

from .models import FinancialMetrics, StockMeta
from .utils import first_existing, to_float


USER_AGENT = "Mozilla/5.0"


def _import_akshare():
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("AkShare is not installed. Run: python -m pip install -r requirements.txt") from exc
    return ak


def _normalize_code(code: object) -> str:
    text = str(code).strip()
    return text.zfill(6) if text.isdigit() else text


def _market_prefix(code: str) -> str:
    if code.startswith(("4", "8", "920")):
        return "bj"
    return "sh" if code.startswith(("5", "6", "9")) else "sz"


def is_non_st_name(name: str) -> bool:
    upper = name.upper()
    bad_markers = ["ST", "*ST", "退", "退市"]
    return not any(marker in upper for marker in bad_markers)


def load_a_share_universe(limit: int | None = None) -> list[StockMeta]:
    try:
        spot = _load_eastmoney_universe_raw(limit=limit)
    except Exception:
        try:
            ak = _import_akshare()
            spot = ak.stock_info_a_code_name().rename(columns={"code": "code", "name": "name"})
        except Exception as exc:
            raise RuntimeError(
                "Failed to load A-share universe. Check network access, proxy settings, or try again later."
            ) from exc

    stocks: list[StockMeta] = []
    for _, row in spot.iterrows():
        code = _normalize_code(first_existing(row, ["code", "symbol", "代码"]))
        name = str(first_existing(row, ["name", "名称"]) or "").strip()
        if not code or not name or not is_non_st_name(name):
            continue
        stocks.append(
            StockMeta(
                code=code,
                name=name,
                market=str(first_existing(row, ["market", "市场"]) or ""),
                pe=to_float(first_existing(row, ["pe", "市盈率-动态", "市盈率"])),
                pb=to_float(first_existing(row, ["pb", "市净率"])),
                turnover_rate=to_float(first_existing(row, ["turnover", "换手率"])),
            )
        )
        if limit and len(stocks) >= limit:
            break
    return stocks


def load_daily_bars(code: str, lookback_calendar_days: int = 45) -> pd.DataFrame:
    datalen = max(10, int(lookback_calendar_days / 7 * 5) + 8)
    loaders = [
        lambda: _load_sina_daily_raw(code, datalen=datalen),
        lambda: _load_tencent_daily_raw(code, datalen=datalen),
    ]
    errors: list[str] = []
    for loader in loaders:
        try:
            bars = normalize_bars(loader())
            if not bars.empty:
                return bars
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError(f"Failed to load daily bars for {code}: {'; '.join(errors)}")


def normalize_bars(raw: pd.DataFrame) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["date", "open", "close", "high", "low", "volume", "amount"])

    mapping = {
        "date": "date",
        "day": "date",
        "日期": "date",
        "open": "open",
        "开盘": "open",
        "close": "close",
        "收盘": "close",
        "high": "high",
        "最高": "high",
        "low": "low",
        "最低": "low",
        "volume": "volume",
        "成交量": "volume",
        "amount": "amount",
        "成交额": "amount",
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


def _load_eastmoney_universe_raw(limit: int | None = None) -> pd.DataFrame:
    fields = "f12,f14,f9,f23,f8"
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"
    rows = []
    page = 1
    page_size = 200
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT})
    while True:
        response = _get_with_retries(
            session,
            "https://push2.eastmoney.com/api/qt/clist/get",
            params={
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f12",
                "fs": fs,
                "fields": fields,
            },
            timeout=12,
        )
        payload = response.json()
        data = payload.get("data") or {}
        diff = data.get("diff") or []
        rows.extend(diff)
        if limit and len(rows) >= limit:
            break
        if len(rows) >= int(data.get("total") or 0) or not diff:
            break
        page += 1

    return pd.DataFrame(
        {
            "code": row.get("f12"),
            "name": row.get("f14"),
            "pe": row.get("f9"),
            "pb": row.get("f23"),
            "turnover": row.get("f8"),
        }
        for row in rows
    )


def _load_sina_daily_raw(code: str, datalen: int) -> pd.DataFrame:
    symbol = f"{_market_prefix(code)}{code}"
    session = requests.Session()
    response = _get_with_retries(
        session,
        "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData",
        params={"symbol": symbol, "scale": 240, "ma": "no", "datalen": datalen},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    data = response.json()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "date": row.get("day"),
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
            "volume": row.get("volume"),
        }
        for row in data
    )


def _load_tencent_daily_raw(code: str, datalen: int) -> pd.DataFrame:
    symbol = f"{_market_prefix(code)}{code}"
    session = requests.Session()
    response = _get_with_retries(
        session,
        "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get",
        params={"param": f"{symbol},day,,,{datalen},qfq"},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    payload = response.json()
    stock_data = (payload.get("data") or {}).get(symbol) or {}
    rows = stock_data.get("qfqday") or stock_data.get("day") or []
    return pd.DataFrame(
        {
            "date": row[0],
            "open": row[1],
            "close": row[2],
            "high": row[3],
            "low": row[4],
            "volume": row[5],
        }
        for row in rows
        if len(row) >= 6
    )


def _get_with_retries(session: requests.Session, url: str, retries: int = 2, **kwargs) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            response = session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_exc = exc
            time.sleep(0.4 * (attempt + 1))
    raise last_exc or RuntimeError(f"Request failed: {url}")


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
