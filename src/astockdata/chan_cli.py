from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import TextIO

from .signals import ChanAnalyzer, ChanSignal, Position
from .symbols import normalize_code


def load_portfolio_csv(path: str) -> list[tuple[str, Position | None]]:
    holdings: list[tuple[str, Position | None]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = normalize_code(row.get("code", ""))
            raw_cost = row.get("cost")
            raw_position = row.get("position")
            if raw_cost in (None, "") and raw_position in (None, ""):
                holdings.append((code, None))
                continue
            if raw_cost in (None, "") or raw_position in (None, ""):
                raise ValueError(f"cost and position must be provided together for {code}")
            cost = float(raw_cost)
            position = float(raw_position)
            if cost <= 0:
                raise ValueError(f"Invalid cost for {code}: {cost}")
            if position < 0 or position > 1:
                raise ValueError(f"Invalid position for {code}: {position}")
            holdings.append((code, Position(cost, position)))
    return holdings


def render_json(signals: list[ChanSignal], out: TextIO = sys.stdout) -> None:
    json.dump([signal.to_dict() for signal in signals], out, ensure_ascii=False, indent=2)
    out.write("\n")


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def render_table(signals: list[ChanSignal], out: TextIO = sys.stdout) -> None:
    headers = ["代码", "动作", "内部信号", "信号力度", "30分钟", "原因", "失效条件"]
    rows = [
        [
            signal.code,
            signal.action,
            signal.signal,
            signal.strength_label or _fmt(signal.confidence),
            signal.confirmation_status or ("缺失" if signal.confirmation_missing else "可用"),
            "；".join(signal.reasons[:2]),
            "；".join(signal.invalidations[:2]) or "-",
        ]
        for signal in signals
    ]
    widths = [max(len(str(row[index])) for row in [headers] + rows) for index in range(len(headers))]
    out.write("  ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + "\n")
    out.write("  ".join("-" * width for width in widths) + "\n")
    for row in rows:
        out.write("  ".join(str(row[index]).ljust(widths[index]) for index in range(len(headers))) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chan-theory A-share trading signal analysis.")
    parser.add_argument("codes", nargs="*", help="A-share codes, e.g. 600519 688017")
    parser.add_argument("--cost", type=float, help="Holding cost for single-stock analysis.")
    parser.add_argument("--position", type=float, help="Position ratio for single-stock analysis, 0 to 1.")
    parser.add_argument("--portfolio", help="CSV file with a code column; cost and position are optional.")
    parser.add_argument("--intraday", action="store_true", help="Mark output as intraday warning.")
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON.")
    return parser


def _single_position(cost: float | None, position: float | None) -> Position | None:
    if cost is None and position is None:
        return None
    if cost is None or position is None:
        raise ValueError("--cost and --position must be provided together")
    if cost <= 0:
        raise ValueError("--cost must be positive")
    if position < 0 or position > 1:
        raise ValueError("--position must be between 0 and 1")
    return Position(cost, position)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    analyzer = ChanAnalyzer()
    try:
        targets: list[tuple[str, Position | None]] = []
        if args.portfolio:
            targets.extend(load_portfolio_csv(args.portfolio))
        position = _single_position(args.cost, args.position)
        targets.extend((normalize_code(code), position) for code in args.codes)
        if not targets:
            raise ValueError("provide at least one code or --portfolio")
        signals = [
            analyzer.analyze(code, position=holding, intraday=args.intraday)
            for code, holding in targets
        ]
    except Exception as exc:
        print(f"chan: {exc}", file=sys.stderr)
        return 1
    if args.json:
        render_json(signals)
    else:
        render_table(signals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
