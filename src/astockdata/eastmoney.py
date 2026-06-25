from __future__ import annotations

import random
import time
from typing import Any

import requests

from .models import ResearchReport, StockInfo
from .symbols import normalize_code, secid


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
REPORT_API = "https://reportapi.eastmoney.com/report/list"
STOCK_INFO_API = "https://push2.eastmoney.com/api/qt/stock/get"


def _float_or_none(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_stock_info(data: dict[str, Any]) -> StockInfo:
    return StockInfo(
        code=str(data.get("f57") or ""),
        name=str(data.get("f58") or ""),
        industry=str(data.get("f127") or ""),
        total_shares=data.get("f84") or 0,
        float_shares=data.get("f85") or 0,
        market_cap=data.get("f116") or 0,
        float_market_cap=data.get("f117") or 0,
        list_date=str(data.get("f189") or ""),
        price=float(data.get("f43") or 0),
    )


def parse_report(row: dict[str, Any]) -> ResearchReport:
    return ResearchReport(
        info_code=str(row.get("infoCode") or ""),
        publish_date=str(row.get("publishDate") or "")[:10],
        org=str(row.get("orgSName") or ""),
        title=str(row.get("title") or ""),
        rating=str(row.get("emRatingName") or ""),
        eps_this_year=_float_or_none(row.get("predictThisYearEps")),
        eps_next_year=_float_or_none(row.get("predictNextYearEps")),
        eps_next_two_year=_float_or_none(row.get("predictNextTwoYearEps")),
    )


class EastmoneyClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        min_interval: float = 1.0,
        jitter: tuple[float, float] = (0.1, 0.5),
    ):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": UA})
        self.min_interval = min_interval
        self.jitter = jitter
        self._last_call = 0.0

    def get(self, url: str, params: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 15):
        wait = self.min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait + random.uniform(*self.jitter))
        try:
            return self.session.get(url, params=params, headers=headers, timeout=timeout)
        finally:
            self._last_call = time.time()

    def stock_info(self, code: str) -> StockInfo:
        code = normalize_code(code)
        params = {
            "fltt": "2",
            "invt": "2",
            "fields": "f57,f58,f84,f85,f127,f116,f117,f189,f43",
            "secid": secid(code),
        }
        response = self.get(STOCK_INFO_API, params=params, headers={"User-Agent": UA}, timeout=10)
        data = response.json().get("data") or {}
        return parse_stock_info(data)

    def reports(self, code: str, max_pages: int = 1) -> list[ResearchReport]:
        code = normalize_code(code)
        reports: list[ResearchReport] = []
        for page in range(1, max_pages + 1):
            params = {
                "industryCode": "*",
                "pageSize": "100",
                "industry": "*",
                "rating": "*",
                "ratingChange": "*",
                "beginTime": "2000-01-01",
                "endTime": "2030-01-01",
                "pageNo": str(page),
                "fields": "",
                "qType": "0",
                "orgCode": "",
                "code": code,
                "rcode": "",
                "p": str(page),
                "pageNum": str(page),
                "pageNumber": str(page),
            }
            response = self.get(
                REPORT_API,
                params=params,
                headers={"Referer": "https://data.eastmoney.com/"},
                timeout=30,
            )
            data = response.json()
            rows = data.get("data") or []
            if not rows:
                break
            reports.extend(parse_report(row) for row in rows)
            if page >= int(data.get("TotalPage") or 1):
                break
        return reports

