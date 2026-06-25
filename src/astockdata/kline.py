from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import requests

from .symbols import normalize_code


@dataclass(frozen=True)
class KLine:
    code: str
    period: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float


class KLineProvider(Protocol):
    def daily_klines(self, code: str) -> list[KLine]:
        ...

    def intraday_klines(self, code: str, period: str = "30m") -> list[KLine]:
        ...


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_baidu_kline_response(code: str, period: str, payload: dict[str, Any]) -> list[KLine]:
    market_data = ((payload.get("Result") or {}).get("newMarketData") or {})
    keys = market_data.get("keys") or []
    raw_rows = str(market_data.get("marketData") or "")
    if not keys or not raw_rows:
        return []
    index = {name: i for i, name in enumerate(keys)}
    required = ["time", "open", "close", "high", "low", "volume", "amount"]
    if any(name not in index for name in required):
        return []

    rows: list[KLine] = []
    for raw_row in raw_rows.split(";"):
        values = raw_row.split(",")
        if len(values) < len(keys):
            continue
        rows.append(
            KLine(
                code=normalize_code(code),
                period=period,
                timestamp=values[index["time"]],
                open=_float(values[index["open"]]),
                high=_float(values[index["high"]]),
                low=_float(values[index["low"]]),
                close=_float(values[index["close"]]),
                volume=_float(values[index["volume"]]),
                amount=_float(values[index["amount"]]),
            )
        )
    return rows


class BaiduDailyKLineProvider:
    def __init__(self, session: requests.Session | None = None, timeout: int = 10):
        self.session = session or requests.Session()
        self.timeout = timeout

    def daily_klines(self, code: str) -> list[KLine]:
        code = normalize_code(code)
        url = "https://finance.pae.baidu.com/selfselect/getstockquotation"
        params = {
            "all": "1",
            "isIndex": "false",
            "isBk": "false",
            "isBlock": "false",
            "isFutures": "false",
            "isStock": "true",
            "newFormat": "1",
            "group": "quotation_kline_ab",
            "finClientType": "pc",
            "code": code,
            "start_time": "",
            "ktype": "1",
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.finance-web.v1+json",
            "Origin": "https://gushitong.baidu.com",
            "Referer": "https://gushitong.baidu.com/",
        }
        response = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
        return parse_baidu_kline_response(code, "1d", response.json())

    def intraday_klines(self, code: str, period: str = "30m") -> list[KLine]:
        return []


class MootdxKLineProvider:
    def daily_klines(self, code: str) -> list[KLine]:
        return []

    def intraday_klines(self, code: str, period: str = "30m") -> list[KLine]:
        try:
            from mootdx.quotes import Quotes
        except Exception:
            return []
        category = 10 if period == "30m" else 4
        try:
            client = Quotes.factory(market="std")
            frame = client.bars(symbol=normalize_code(code), category=category, offset=120)
        except Exception:
            return []
        if frame is None:
            return []
        rows: list[KLine] = []
        for _, row in frame.iterrows():
            rows.append(
                KLine(
                    code=normalize_code(code),
                    period=period,
                    timestamp=str(row.get("datetime", "")),
                    open=float(row.get("open", 0)),
                    high=float(row.get("high", 0)),
                    low=float(row.get("low", 0)),
                    close=float(row.get("close", 0)),
                    volume=float(row.get("vol", 0)),
                    amount=float(row.get("amount", 0)),
                )
            )
        return rows

