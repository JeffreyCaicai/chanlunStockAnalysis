from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from .backtest import run_signal_backtest
from .signals import ChanAnalyzer, Position
from .web_static import INDEX_HTML


Headers = dict[str, str]


def _json_response(status: int, payload: dict[str, Any]) -> tuple[int, Headers, str]:
    return status, {"Content-Type": "application/json; charset=utf-8"}, json.dumps(payload, ensure_ascii=False)


def _html_response() -> tuple[int, Headers, str]:
    return 200, {"Content-Type": "text/html; charset=utf-8"}, INDEX_HTML


def _position_from_payload(payload: dict[str, Any]) -> Position | None:
    has_cost = payload.get("cost") not in (None, "")
    has_position = payload.get("position") not in (None, "")
    if not has_cost and not has_position:
        return None
    if not has_cost or not has_position:
        raise ValueError("cost and position must be provided together")
    cost = float(payload["cost"])
    position = float(payload["position"])
    if cost <= 0:
        raise ValueError("cost must be positive")
    if position < 0 or position > 1:
        raise ValueError("position must be between 0 and 1")
    return Position(cost, position)


def _horizons_from_payload(payload: dict[str, Any]) -> list[int]:
    raw_horizons = payload.get("horizons", [5, 10, 20])
    if not isinstance(raw_horizons, list):
        raise ValueError("horizons must be a list of positive integers")
    horizons = [int(item) for item in raw_horizons]
    if not horizons or any(item <= 0 for item in horizons):
        raise ValueError("horizons must be positive integers")
    return horizons


def _min_history_from_payload(payload: dict[str, Any]) -> int:
    value = int(payload.get("min_history", 60))
    if value <= 0:
        raise ValueError("min_history must be positive")
    return value


def _run_backtest(analyzer: ChanAnalyzer, query: str, payload: dict[str, Any]) -> dict[str, Any]:
    identity = analyzer.resolver.resolve(query)
    daily_rows = analyzer.kline_provider.daily_klines(identity.code)
    if not daily_rows:
        raise RuntimeError(f"No daily K-line data returned for {identity.code}")
    report = run_signal_backtest(
        identity.code,
        daily_rows,
        horizons=_horizons_from_payload(payload),
        min_history=_min_history_from_payload(payload),
        engine=analyzer.engine,
    )
    return {
        "code": identity.code,
        "stock_name": identity.name,
        "report": report.to_dict(),
    }


def handle_api_request(method: str, path: str, body: bytes, analyzer: ChanAnalyzer) -> tuple[int, Headers, str]:
    route = urlparse(path).path
    if method == "GET" and route == "/":
        return _html_response()
    if method == "GET" and route == "/api/health":
        return _json_response(
            200,
            {
                "status": "ok",
                "daily_source": "baidu_http",
                "confirm_source": "mootdx_optional",
            },
        )
    if method == "POST" and route == "/api/analyze":
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
            code = str(payload.get("code") or "").strip()
            if not code:
                return _json_response(400, {"error": "code is required"})
            signal = analyzer.analyze(
                code,
                position=_position_from_payload(payload),
                intraday=bool(payload.get("intraday", False)),
            )
            return _json_response(200, signal.to_dict())
        except Exception as exc:
            return _json_response(400, {"error": str(exc)})
    if method == "POST" and route == "/api/backtest":
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
            code = str(payload.get("code") or "").strip()
            if not code:
                return _json_response(400, {"error": "code is required"})
            return _json_response(200, _run_backtest(analyzer, code, payload))
        except Exception as exc:
            return _json_response(400, {"error": str(exc)})
    if method == "POST" and route == "/api/analyze-portfolio":
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
            holdings = payload.get("holdings") or []
            results = []
            for item in holdings:
                code = str(item.get("code") or "").strip()
                if not code:
                    return _json_response(400, {"error": "code is required"})
                results.append(
                    analyzer.analyze(
                        code,
                        position=_position_from_payload(item),
                        intraday=bool(payload.get("intraday", False)),
                    ).to_dict()
                )
            return _json_response(200, {"results": results})
        except Exception as exc:
            return _json_response(400, {"error": str(exc)})
    return _json_response(404, {"error": "not found"})


def make_handler(analyzer: ChanAnalyzer):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, headers: Headers, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self) -> None:
            status, headers, body = handle_api_request("GET", self.path, b"", analyzer)
            self._send(status, headers, body)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            status, headers, body = handle_api_request("POST", self.path, raw_body, analyzer)
            self._send(status, headers, body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local Chan signal Web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    server = HTTPServer((args.host, args.port), make_handler(ChanAnalyzer()))
    print(f"Serving Chan signal UI at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
