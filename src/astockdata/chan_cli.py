from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import TextIO

from .backtest import BacktestBucketSummary, BacktestReport, run_signal_backtest
from .kline import BaiduDailyKLineProvider
from .resolver import EastmoneyStockResolver
from .signals import ChanAnalyzer, ChanSignal, Position


def load_portfolio_csv(path: str) -> list[tuple[str, Position | None]]:
    holdings: list[tuple[str, Position | None]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            code = str(row.get("code", "")).strip()
            if not code:
                raise ValueError("code is required")
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


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}%"


def _veto_label(signal: ChanSignal) -> str:
    context = signal.veto_context
    if context is None or not context.vetoed:
        return "未触发"
    return "已否决买入"


def parse_horizons(raw: str) -> list[int]:
    values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not values or any(value <= 0 for value in values):
        raise ValueError("horizons must be positive integers")
    return values


def render_table(signals: list[ChanSignal], out: TextIO = sys.stdout) -> None:
    headers = ["代码", "动作", "内部信号", "买卖点", "环境", "辅助", "否决条件", "信号力度", "30分钟", "原因", "失效条件"]
    rows = [
        [
            signal.code,
            signal.action,
            signal.signal,
            signal.trade_point.label if signal.trade_point else "-",
            signal.market_context.label if signal.market_context else "-",
            signal.technical_context.label if signal.technical_context else "-",
            _veto_label(signal),
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


def _render_bucket_section(title: str, rows: list[BacktestBucketSummary], out: TextIO) -> None:
    out.write(f"\n{title}\n")
    headers = ["分组", "样本数", "有利次数", "有利率", "平均收益", "平均最大有利", "平均最大不利"]
    table = [
        [
            row.name,
            row.sample_count,
            row.favorable_count,
            _fmt_pct(row.favorable_rate * 100 if row.favorable_rate is not None else None),
            _fmt_pct(row.average_return_pct),
            _fmt_pct(row.average_max_favorable_pct),
            _fmt_pct(row.average_max_adverse_pct),
        ]
        for row in rows
    ]
    widths = [max(len(str(row[index])) for row in [headers] + table) for index in range(len(headers))]
    out.write("  ".join(headers[index].ljust(widths[index]) for index in range(len(headers))) + "\n")
    out.write("  ".join("-" * width for width in widths) + "\n")
    for row in table:
        out.write("  ".join(str(row[index]).ljust(widths[index]) for index in range(len(headers))) + "\n")


def render_backtest_table(report: BacktestReport, out: TextIO = sys.stdout) -> None:
    out.write(f"回测摘要：{report.summary}\n")
    out.write(f"代码：{report.code}  区间：{report.start_timestamp or '-'} -> {report.end_timestamp or '-'}\n")
    _render_bucket_section("按周期", report.by_horizon, out)
    _render_bucket_section("按动作", report.by_action, out)
    _render_bucket_section("按买卖点", report.by_trade_point, out)
    _render_bucket_section("按信号力度", report.by_strength, out)
    _render_bucket_section("按辅助确认", report.by_technical, out)


def render_backtest_json(report: BacktestReport, out: TextIO = sys.stdout) -> None:
    json.dump(report.to_dict(), out, ensure_ascii=False, indent=2)
    out.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chan-theory A-share trading signal analysis.")
    parser.add_argument("codes", nargs="*", help="A-share codes, e.g. 600519 688017")
    parser.add_argument("--cost", type=float, help="Holding cost for single-stock analysis.")
    parser.add_argument("--position", type=float, help="Position ratio for single-stock analysis, 0 to 1.")
    parser.add_argument("--portfolio", help="CSV file with a code column; cost and position are optional.")
    parser.add_argument("--intraday", action="store_true", help="Mark output as intraday warning.")
    parser.add_argument("--json", action="store_true", help="Render machine-readable JSON.")
    parser.add_argument("--backtest", help="Run historical signal validation for one code or stock name.")
    parser.add_argument("--horizons", default="5,10,20", help="Comma-separated forward horizons for --backtest.")
    parser.add_argument("--lookback", type=int, default=260, help="Limit daily K-lines used by --backtest.")
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
    try:
        if args.backtest:
            horizons = parse_horizons(args.horizons)
            identity = EastmoneyStockResolver().resolve(args.backtest)
            rows = BaiduDailyKLineProvider().daily_klines(identity.code)
            if args.lookback and args.lookback > 0:
                rows = rows[-args.lookback :]
            report = run_signal_backtest(identity.code, rows, horizons=horizons)
            if args.json:
                render_backtest_json(report)
            else:
                render_backtest_table(report)
            return 0

        analyzer = ChanAnalyzer()
        targets: list[tuple[str, Position | None]] = []
        if args.portfolio:
            targets.extend(load_portfolio_csv(args.portfolio))
        position = _single_position(args.cost, args.position)
        targets.extend((code, position) for code in args.codes)
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
