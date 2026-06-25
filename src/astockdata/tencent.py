from __future__ import annotations

import urllib.request

from .models import Quote
from .symbols import market_prefix, normalize_code


def _float_at(values: list[str], index: int) -> float:
    if index >= len(values) or values[index] == "":
        return 0.0
    try:
        return float(values[index])
    except ValueError:
        return 0.0


def parse_tencent_response(raw: str) -> list[Quote]:
    quotes: list[Quote] = []
    for line in raw.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=", 1)[0].split("_")[-1]
        values = line.split('"')[1].split("~")
        if len(values) < 53:
            continue
        code = key[2:]
        quotes.append(
            Quote(
                code=code,
                name=values[1],
                price=_float_at(values, 3),
                last_close=_float_at(values, 4),
                open=_float_at(values, 5),
                change_amount=_float_at(values, 31),
                change_pct=_float_at(values, 32),
                high=_float_at(values, 33),
                low=_float_at(values, 34),
                amount_wan=_float_at(values, 37),
                turnover_pct=_float_at(values, 38),
                pe_ttm=_float_at(values, 39),
                amplitude_pct=_float_at(values, 43),
                market_cap_yi=_float_at(values, 44),
                float_market_cap_yi=_float_at(values, 45),
                pb=_float_at(values, 46),
                limit_up=_float_at(values, 47),
                limit_down=_float_at(values, 48),
                volume_ratio=_float_at(values, 49),
                pe_static=_float_at(values, 52),
            )
        )
    return quotes


class TencentClient:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def quotes(self, codes: list[str]) -> dict[str, Quote]:
        normalized = [normalize_code(code) for code in codes]
        prefixed = [f"{market_prefix(code)}{code}" for code in normalized]
        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=self.timeout)
        raw = resp.read().decode("gbk")
        return {quote.code: quote for quote in parse_tencent_response(raw)}

