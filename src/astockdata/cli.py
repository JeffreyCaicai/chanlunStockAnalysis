from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import TextIO

from .analysis import Analyzer
from .models import ValuationResult


def render_json(results: list[ValuationResult], out: TextIO = sys.stdout) -> None:
    payload = [result.to_dict() for result in results]
    json.dump(payload, out, ensure_ascii=False, indent=2)
    out.write("\n")


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def render_table(results: list[ValuationResult], out: TextIO = sys.stdout) -> None:
    headers = ["代码", "名称", "行业", "价格", "PE(TTM)", "PB", "市值(亿)", "EPS", "次年EPS", "前向PE", "增速%", "PEG", "消化年", "研报数"]
    rows = [
        [
            result.code,
            result.name,
            result.industry,
            _fmt(result.price),
            _fmt(result.pe_ttm),
            _fmt(result.pb),
            _fmt(result.market_cap_yi),
            _fmt(result.eps_this_year),
            _fmt(result.eps_next_year),
            _fmt(result.forward_pe),
            _fmt(result.growth_pct),
            _fmt(result.peg),
            _fmt(result.pe_digest_years),
            str(result.eps_report_count),
        ]
        for result in results
    ]
    widths = [
        max(len(str(row[index])) for row in [headers] + rows)
        for index in range(len(headers))
    ]
    out.write("  ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + "\n")
    out.write("  ".join("-" * width for width in widths) + "\n")
    for row in rows:
        out.write("  ".join(str(row[index]).ljust(widths[index]) for index in range(len(headers))) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A-share valuation analysis using Tencent and Eastmoney endpoints.")
    parser.add_argument("codes", nargs="+", help="A-share codes, e.g. 600519 688017")
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON instead of a table.")
    parser.add_argument("--report-pages", type=int, default=1, help="Eastmoney report pages to fetch per stock.")
    parser.add_argument("--max-reports", type=int, default=20, help="Latest reports to include in EPS aggregation.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    analyzer = Analyzer(report_pages=args.report_pages, max_reports=args.max_reports)
    try:
        results = analyzer.compare(args.codes)
    except Exception as exc:
        print(f"astock: {exc}", file=sys.stderr)
        return 1
    if args.json:
        render_json(results)
    else:
        render_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
