from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
import urllib.request

import requests

from .eastmoney import EastmoneyClient, UA
from .tencent import parse_tencent_response


BOARD_LIST_API = "https://push2.eastmoney.com/api/qt/clist/get"


@dataclass(frozen=True)
class IndexSnapshot:
    code: str
    name: str
    change_pct: float


@dataclass(frozen=True)
class BoardSnapshot:
    code: str
    name: str
    change_pct: float
    turnover_pct: float


@dataclass(frozen=True)
class MarketContext:
    label: str
    score: float
    index: IndexSnapshot | None
    industry: str
    sector: BoardSnapshot | None
    summary: str
    reasons: list[str]
    risk_notes: list[str]


class MarketContextProvider(Protocol):
    def context_for(self, code: str) -> MarketContext:
        ...


def neutral_market_context(industry: str = "", reason: str = "市场环境数据暂不可用") -> MarketContext:
    return MarketContext(
        label="中性",
        score=0.5,
        index=None,
        industry=industry,
        sector=None,
        summary=reason,
        reasons=[reason],
        risk_notes=[],
    )


def _score_change(change_pct: float, strong: float = 1.0) -> float:
    if change_pct >= strong:
        return 0.2
    if change_pct > 0:
        return 0.08
    if change_pct <= -strong:
        return -0.2
    if change_pct < 0:
        return -0.08
    return 0.0


def _label(score: float) -> str:
    if score >= 0.65:
        return "顺风"
    if score <= 0.4:
        return "逆风"
    return "中性"


def _clamp(value: float, low: float = 0.05, high: float = 0.95) -> float:
    return max(low, min(high, value))


def match_sector(industry: str, sectors: list[BoardSnapshot]) -> BoardSnapshot | None:
    name = industry.strip()
    if not name:
        return None
    for sector in sectors:
        if sector.name == name:
            return sector
    for sector in sectors:
        if sector.name and (sector.name in name or name in sector.name):
            return sector
    return None


def build_market_context(
    index: IndexSnapshot | None,
    industry: str = "",
    sector: BoardSnapshot | None = None,
) -> MarketContext:
    score = 0.5
    reasons: list[str] = []
    risk_notes: list[str] = []
    parts: list[str] = []

    if index is None:
        reasons.append("大盘指数数据暂不可用")
        parts.append("大盘数据暂不可用")
    else:
        score += _score_change(index.change_pct)
        direction = "上涨" if index.change_pct >= 0 else "下跌"
        parts.append(f"{index.name}{direction}{abs(index.change_pct):.2f}%")
        reasons.append(parts[-1])

    if sector is None:
        if industry:
            parts.append(f"{industry}暂未匹配到行业板块")
            reasons.append(f"{industry}暂未匹配到行业板块")
        else:
            parts.append("行业板块数据暂不可用")
            reasons.append("行业板块数据暂不可用")
    else:
        score += _score_change(sector.change_pct)
        direction = "上涨" if sector.change_pct >= 0 else "下跌"
        parts.append(f"{sector.name}{direction}{abs(sector.change_pct):.2f}%")
        reasons.append(parts[-1])

    score = round(_clamp(score), 2)
    label = _label(score)
    if index is not None and sector is not None and index.change_pct <= -1.0 and sector.change_pct <= -1.0:
        risk_notes.append("大盘和板块都偏弱")
    elif sector is not None and sector.change_pct <= -1.0:
        risk_notes.append("板块偏弱")
    elif index is not None and index.change_pct <= -1.0:
        risk_notes.append("大盘偏弱")

    return MarketContext(
        label=label,
        score=score,
        index=index,
        industry=industry,
        sector=sector,
        summary="；".join(parts),
        reasons=reasons,
        risk_notes=risk_notes,
    )


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def parse_board_rows(rows: list[dict[str, Any]]) -> list[BoardSnapshot]:
    return [
        BoardSnapshot(
            code=str(row.get("f12") or ""),
            name=str(row.get("f14") or ""),
            change_pct=_float(row.get("f3")),
            turnover_pct=_float(row.get("f8")),
        )
        for row in rows
        if row.get("f12") and row.get("f14")
    ]


class TencentIndexProvider:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def index_snapshot(self, prefixed_code: str = "sh000300") -> IndexSnapshot | None:
        url = "https://qt.gtimg.cn/q=" + prefixed_code
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=self.timeout)
        raw = resp.read().decode("gbk")
        quotes = parse_tencent_response(raw)
        if not quotes:
            return None
        quote = quotes[0]
        return IndexSnapshot(code=quote.code, name=quote.name, change_pct=quote.change_pct)


class EastmoneyBoardProvider:
    def __init__(self, session: requests.Session | None = None, timeout: int = 10):
        self.session = session or requests.Session()
        self.timeout = timeout

    def boards(self) -> list[BoardSnapshot]:
        params = {
            "pn": "1",
            "pz": "300",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:90+t:2",
            "fields": "f12,f14,f3,f8",
        }
        response = self.session.get(
            BOARD_LIST_API,
            params=params,
            headers={"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"},
            timeout=self.timeout,
        )
        rows = (response.json().get("data") or {}).get("diff") or []
        return parse_board_rows(rows)


class HttpMarketContextProvider:
    def __init__(
        self,
        eastmoney: EastmoneyClient | None = None,
        index_provider: TencentIndexProvider | None = None,
        board_provider: EastmoneyBoardProvider | None = None,
    ):
        self.eastmoney = eastmoney or EastmoneyClient()
        self.index_provider = index_provider or TencentIndexProvider()
        self.board_provider = board_provider or EastmoneyBoardProvider()

    def context_for(self, code: str) -> MarketContext:
        industry = ""
        try:
            info = self.eastmoney.stock_info(code)
            industry = info.industry or ""
            index = self.index_provider.index_snapshot("sh000300")
            sector = match_sector(industry, self.board_provider.boards())
            return build_market_context(index=index, industry=industry, sector=sector)
        except Exception as exc:
            return neutral_market_context(industry=industry, reason=f"市场环境数据暂不可用：{exc}")
