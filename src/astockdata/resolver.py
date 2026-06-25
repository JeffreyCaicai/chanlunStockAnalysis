from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import requests

from .symbols import normalize_code


SUGGEST_API = "https://searchapi.eastmoney.com/api/suggest/get"
SUGGEST_TOKEN = "44c9d251add88e27b65ed86506f6e5da"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


@dataclass(frozen=True)
class StockIdentity:
    code: str
    name: str = ""
    query: str = ""


class StockResolver(Protocol):
    def resolve(self, query: str) -> StockIdentity:
        ...


class EastmoneyStockResolver:
    def __init__(self, session: requests.Session | None = None, timeout: int = 10):
        self.session = session or requests.Session()
        self.timeout = timeout

    def resolve(self, query: str) -> StockIdentity:
        text = query.strip()
        if not text:
            raise ValueError("stock code or name is required")
        code_fallback = self._normalize_if_code(text)
        try:
            identity = self._resolve_from_suggest(text)
        except Exception:
            if code_fallback:
                return StockIdentity(code=code_fallback, query=text)
            raise
        if identity is not None:
            return identity
        if code_fallback:
            return StockIdentity(code=code_fallback, query=text)
        raise ValueError(f"Cannot resolve stock code or name: {query!r}")

    def _resolve_from_suggest(self, query: str) -> StockIdentity | None:
        response = self.session.get(
            SUGGEST_API,
            params={
                "input": query,
                "type": "14",
                "token": SUGGEST_TOKEN,
            },
            headers={"User-Agent": UA},
            timeout=self.timeout,
        )
        rows = (((response.json().get("QuotationCodeTable") or {}).get("Data")) or [])
        for row in rows:
            identity = self._identity_from_row(row, query)
            if identity is not None:
                return identity
        return None

    @staticmethod
    def _normalize_if_code(query: str) -> str | None:
        try:
            return normalize_code(query)
        except ValueError:
            return None

    @staticmethod
    def _identity_from_row(row: dict[str, Any], query: str) -> StockIdentity | None:
        raw_code = str(row.get("Code") or row.get("UnifiedCode") or "")
        try:
            code = normalize_code(raw_code)
        except ValueError:
            return None
        name = str(row.get("Name") or "")
        return StockIdentity(code=code, name=name, query=query)
