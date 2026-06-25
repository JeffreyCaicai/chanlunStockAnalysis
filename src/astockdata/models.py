from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Quote:
    code: str
    name: str
    price: float
    last_close: float
    open: float
    change_amount: float
    change_pct: float
    high: float
    low: float
    amount_wan: float
    turnover_pct: float
    pe_ttm: float
    amplitude_pct: float
    market_cap_yi: float
    float_market_cap_yi: float
    pb: float
    limit_up: float
    limit_down: float
    volume_ratio: float
    pe_static: float


@dataclass(frozen=True)
class StockInfo:
    code: str
    name: str
    industry: str
    total_shares: int | float
    float_shares: int | float
    market_cap: int | float
    float_market_cap: int | float
    list_date: str
    price: float

    @property
    def market_cap_yi(self) -> float:
        return round(float(self.market_cap or 0) / 100_000_000, 2)

    @property
    def float_market_cap_yi(self) -> float:
        return round(float(self.float_market_cap or 0) / 100_000_000, 2)


@dataclass(frozen=True)
class ResearchReport:
    info_code: str
    publish_date: str
    org: str
    title: str
    rating: str
    eps_this_year: float | None
    eps_next_year: float | None
    eps_next_two_year: float | None


@dataclass(frozen=True)
class EpsEstimate:
    eps_this_year: float | None
    eps_next_year: float | None
    eps_next_two_year: float | None
    report_count: int
    org_count: int


@dataclass(frozen=True)
class ValuationResult:
    code: str
    name: str
    industry: str
    price: float
    pe_ttm: float
    pb: float
    market_cap_yi: float
    eps_this_year: float | None
    eps_next_year: float | None
    eps_report_count: int
    forward_pe: float | None
    growth_pct: float | None
    peg: float | None
    pe_digest_years: float | None
    rating_summary: dict[str, int] = field(default_factory=dict)
    latest_reports: list[ResearchReport] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

