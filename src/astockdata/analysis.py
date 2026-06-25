from __future__ import annotations

import math
import statistics
from collections import Counter
from typing import Protocol

from .eastmoney import EastmoneyClient
from .models import EpsEstimate, Quote, ResearchReport, StockInfo, ValuationResult
from .symbols import normalize_code
from .tencent import TencentClient


class MarketData(Protocol):
    def quotes(self, codes: list[str]) -> dict[str, Quote]:
        ...

    def stock_info(self, code: str) -> StockInfo:
        ...

    def reports_for(self, code: str, max_pages: int = 1) -> list[ResearchReport]:
        ...


class HttpMarketData:
    def __init__(self, tencent: TencentClient | None = None, eastmoney: EastmoneyClient | None = None):
        self.tencent = tencent or TencentClient()
        self.eastmoney = eastmoney or EastmoneyClient()

    def quotes(self, codes: list[str]) -> dict[str, Quote]:
        return self.tencent.quotes(codes)

    def stock_info(self, code: str) -> StockInfo:
        return self.eastmoney.stock_info(code)

    def reports_for(self, code: str, max_pages: int = 1) -> list[ResearchReport]:
        return self.eastmoney.reports(code, max_pages=max_pages)


def _median(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return float(statistics.median(present))


def aggregate_eps(reports: list[ResearchReport]) -> EpsEstimate:
    eps_this = _median([report.eps_this_year for report in reports])
    eps_next = _median([report.eps_next_year for report in reports])
    eps_next_two = _median([report.eps_next_two_year for report in reports])
    orgs = {report.org for report in reports if report.org}
    return EpsEstimate(
        eps_this_year=eps_this,
        eps_next_year=eps_next,
        eps_next_two_year=eps_next_two,
        report_count=len(reports),
        org_count=len(orgs),
    )


def recent_reports(reports: list[ResearchReport], limit: int = 20) -> list[ResearchReport]:
    return sorted(reports, key=lambda report: report.publish_date, reverse=True)[:limit]


def forward_pe(price: float, eps: float | None) -> float | None:
    if eps is None or eps <= 0:
        return None
    return price / eps


def growth_rate(eps_this_year: float | None, eps_next_year: float | None) -> float | None:
    if eps_this_year is None or eps_next_year is None or eps_this_year <= 0:
        return None
    return eps_next_year / eps_this_year - 1


def calc_peg(pe: float | None, growth: float | None) -> float | None:
    if pe is None or growth is None or growth <= 0:
        return None
    return pe / (growth * 100)


def pe_digest_years(current_pe: float | None, growth: float | None, target_pe: float = 30.0) -> float | None:
    if current_pe is None:
        return None
    if current_pe <= target_pe:
        return 0.0
    if growth is None or growth <= 0:
        return None
    return math.log(current_pe / target_pe) / math.log(1 + growth)


def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


class Analyzer:
    def __init__(self, market_data: MarketData | None = None, report_pages: int = 1, max_reports: int = 20):
        self.market_data = market_data or HttpMarketData()
        self.report_pages = report_pages
        self.max_reports = max_reports

    def analyze_stock(self, code: str) -> ValuationResult:
        code = normalize_code(code)
        quote = self.market_data.quotes([code]).get(code)
        if quote is None:
            raise RuntimeError(f"No Tencent quote returned for {code}")
        info = self.market_data.stock_info(code)
        reports = recent_reports(self.market_data.reports_for(code, max_pages=self.report_pages), self.max_reports)
        eps = aggregate_eps(reports)
        fpe = forward_pe(quote.price, eps.eps_this_year)
        growth = growth_rate(eps.eps_this_year, eps.eps_next_year)
        peg = calc_peg(fpe, growth)
        digest = pe_digest_years(fpe, growth)
        ratings = Counter(report.rating for report in reports if report.rating)
        industry = info.industry or ""
        return ValuationResult(
            code=code,
            name=quote.name or info.name,
            industry=industry,
            price=quote.price,
            pe_ttm=quote.pe_ttm,
            pb=quote.pb,
            market_cap_yi=quote.market_cap_yi or info.market_cap_yi,
            eps_this_year=_round(eps.eps_this_year),
            eps_next_year=_round(eps.eps_next_year),
            eps_report_count=eps.report_count,
            forward_pe=_round(fpe),
            growth_pct=_round(growth * 100 if growth is not None else None),
            peg=_round(peg),
            pe_digest_years=_round(digest),
            rating_summary=dict(ratings),
            latest_reports=reports[:5],
        )

    def compare(self, codes: list[str]) -> list[ValuationResult]:
        return [self.analyze_stock(code) for code in codes]
