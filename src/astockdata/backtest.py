from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Callable

from .chan import analyze_structure
from .kline import KLine
from .signals import ChanSignal, ChanSignalEngine
from .technical_context import build_technical_context


@dataclass(frozen=True)
class BacktestSample:
    code: str
    timestamp: str
    action: str
    signal: str
    confidence: float
    strength_label: str
    trade_point_label: str
    technical_label: str
    entry_price: float
    horizon_days: int
    exit_price: float
    return_pct: float
    favorable: bool
    max_favorable_pct: float
    max_adverse_pct: float


@dataclass(frozen=True)
class BacktestBucketSummary:
    name: str
    sample_count: int
    favorable_count: int
    favorable_rate: float | None
    average_return_pct: float | None
    average_max_favorable_pct: float | None
    average_max_adverse_pct: float | None
    best_return_pct: float | None
    worst_return_pct: float | None


@dataclass(frozen=True)
class BacktestReport:
    code: str
    start_timestamp: str | None
    end_timestamp: str | None
    horizons: list[int]
    sample_count: int
    skipped_hold_count: int
    by_horizon: list[BacktestBucketSummary]
    by_action: list[BacktestBucketSummary]
    by_trade_point: list[BacktestBucketSummary]
    by_strength: list[BacktestBucketSummary]
    by_technical: list[BacktestBucketSummary]
    samples: list[BacktestSample]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def summarize_samples(name: str, samples: list[BacktestSample]) -> BacktestBucketSummary:
    if not samples:
        return BacktestBucketSummary(
            name=name,
            sample_count=0,
            favorable_count=0,
            favorable_rate=None,
            average_return_pct=None,
            average_max_favorable_pct=None,
            average_max_adverse_pct=None,
            best_return_pct=None,
            worst_return_pct=None,
        )
    favorable_count = sum(1 for sample in samples if sample.favorable)
    return BacktestBucketSummary(
        name=name,
        sample_count=len(samples),
        favorable_count=favorable_count,
        favorable_rate=round(favorable_count / len(samples), 2),
        average_return_pct=_average([sample.return_pct for sample in samples]),
        average_max_favorable_pct=_average([sample.max_favorable_pct for sample in samples]),
        average_max_adverse_pct=_average([sample.max_adverse_pct for sample in samples]),
        best_return_pct=round(max(sample.return_pct for sample in samples), 2),
        worst_return_pct=round(min(sample.return_pct for sample in samples), 2),
    )


def _pct(current: float, base: float) -> float:
    if base <= 0:
        return 0.0
    return (current - base) / base * 100


def _inverse_pct(current: float, base: float) -> float:
    if base <= 0:
        return 0.0
    return (base - current) / base * 100


def _trade_point_label(signal: ChanSignal) -> str:
    if signal.trade_point is None:
        return "无明确买卖点"
    return signal.trade_point.label


def _technical_label(signal: ChanSignal) -> str:
    if signal.technical_context is None:
        return "-"
    return signal.technical_context.label


def build_outcome_sample(
    code: str,
    signal: ChanSignal,
    entry: KLine,
    future_rows: list[KLine],
    horizon_days: int,
) -> BacktestSample:
    exit_row = future_rows[horizon_days - 1]
    if signal.action == "卖出":
        return_pct = _inverse_pct(exit_row.close, entry.close)
        max_favorable = max(0.0, _inverse_pct(min(row.low for row in future_rows), entry.close))
        max_adverse = min(0.0, -_pct(max(row.high for row in future_rows), entry.close))
    else:
        return_pct = _pct(exit_row.close, entry.close)
        max_favorable = max(0.0, _pct(max(row.high for row in future_rows), entry.close))
        max_adverse = min(0.0, _pct(min(row.low for row in future_rows), entry.close))
    return BacktestSample(
        code=code,
        timestamp=entry.timestamp,
        action=signal.action,
        signal=signal.signal,
        confidence=signal.confidence,
        strength_label=signal.strength_label,
        trade_point_label=_trade_point_label(signal),
        technical_label=_technical_label(signal),
        entry_price=round(entry.close, 2),
        horizon_days=horizon_days,
        exit_price=round(exit_row.close, 2),
        return_pct=round(return_pct, 2),
        favorable=return_pct > 0,
        max_favorable_pct=round(max_favorable, 2),
        max_adverse_pct=round(max_adverse, 2),
    )


def _group(
    samples: list[BacktestSample],
    key: Callable[[BacktestSample], str],
) -> list[BacktestBucketSummary]:
    buckets: dict[str, list[BacktestSample]] = defaultdict(list)
    for sample in samples:
        buckets[str(key(sample))].append(sample)
    return [summarize_samples(name, buckets[name]) for name in sorted(buckets)]


def _empty_report(code: str, rows: list[KLine], horizons: list[int], summary: str) -> BacktestReport:
    return BacktestReport(
        code=code,
        start_timestamp=rows[0].timestamp if rows else None,
        end_timestamp=rows[-1].timestamp if rows else None,
        horizons=horizons,
        sample_count=0,
        skipped_hold_count=0,
        by_horizon=[],
        by_action=[],
        by_trade_point=[],
        by_strength=[],
        by_technical=[],
        samples=[],
        summary=summary,
    )


def _group_by_horizon(samples: list[BacktestSample], horizons: list[int]) -> list[BacktestBucketSummary]:
    return [
        summarize_samples(f"{horizon}日", [sample for sample in samples if sample.horizon_days == horizon])
        for horizon in horizons
    ]


def run_signal_backtest(
    code: str,
    rows: list[KLine],
    horizons: list[int] | None = None,
    min_history: int = 60,
    engine: ChanSignalEngine | None = None,
) -> BacktestReport:
    horizons = horizons or [5, 10, 20]
    if not horizons:
        return _empty_report(code, rows, horizons, "观察周期为空，无法形成回测统计。")
    max_horizon = max(horizons)
    if len(rows) < min_history + max_horizon:
        return _empty_report(code, rows, horizons, "样本不足，无法形成可靠回测统计。")

    engine = engine or ChanSignalEngine()
    samples: list[BacktestSample] = []
    skipped_hold_count = 0
    last_entry_index = len(rows) - max_horizon - 1

    for index in range(min_history - 1, last_entry_index + 1):
        history = rows[: index + 1]
        signal = engine.evaluate(
            code=code,
            daily_structure=analyze_structure(history),
            confirm_structure=None,
            latest_price=history[-1].close,
            recent_klines=history,
            technical_context=build_technical_context(history),
        )
        if signal.action not in {"买入", "卖出"}:
            skipped_hold_count += 1
            continue
        for horizon in horizons:
            future_rows = rows[index + 1 : index + 1 + horizon]
            if len(future_rows) < horizon:
                continue
            samples.append(build_outcome_sample(code, signal, rows[index], future_rows, horizon))

    return BacktestReport(
        code=code,
        start_timestamp=rows[0].timestamp,
        end_timestamp=rows[-1].timestamp,
        horizons=horizons,
        sample_count=len(samples),
        skipped_hold_count=skipped_hold_count,
        by_horizon=_group_by_horizon(samples, horizons),
        by_action=_group(samples, lambda sample: sample.action),
        by_trade_point=_group(samples, lambda sample: sample.trade_point_label),
        by_strength=_group(samples, lambda sample: sample.strength_label),
        by_technical=_group(samples, lambda sample: sample.technical_label),
        samples=samples,
        summary=f"共生成{len(samples)}条买卖信号回测样本，跳过{skipped_hold_count}条继续持有信号。",
    )
