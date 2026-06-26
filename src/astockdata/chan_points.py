from __future__ import annotations

from dataclasses import dataclass

from .chan import ChanStructure, Fractal, Stroke, analyze_structure
from .kline import KLine


@dataclass(frozen=True)
class TradePoint:
    kind: str
    label: str
    action_bias: str
    timestamp: str | None
    price: float | None
    score: float
    explanation: str
    invalidation: str


@dataclass(frozen=True)
class TradePointReplaySample:
    timestamp: str
    entry_price: float
    exit_price: float


@dataclass(frozen=True)
class TradePointReplay:
    kind: str
    label: str
    horizon_days: int
    sample_count: int
    favorable_count: int
    favorable_rate: float | None
    average_return_pct: float | None
    best_return_pct: float | None
    worst_return_pct: float | None
    summary: str


def _empty_point() -> TradePoint:
    return TradePoint(
        kind="none",
        label="无明确买卖点",
        action_bias="neutral",
        timestamp=None,
        price=None,
        score=0.0,
        explanation="当前结构还没有形成清晰的一买、二买、三买或卖点。",
        invalidation="-",
    )


def _last_fractal(structure: ChanStructure, kind: str) -> Fractal | None:
    selected = [item for item in structure.fractals if item.kind == kind]
    return selected[-1] if selected else None


def _previous_fractal_before(structure: ChanStructure, kind: str, index: int) -> Fractal | None:
    selected = [item for item in structure.fractals if item.kind == kind and item.index < index]
    return selected[-1] if selected else None


def _last_three_directions(strokes: list[Stroke]) -> list[str]:
    return [item.direction for item in strokes[-3:]]


def _point(
    kind: str,
    label: str,
    action_bias: str,
    fractal: Fractal | None,
    score: float,
    explanation: str,
    invalidation: str,
) -> TradePoint:
    return TradePoint(
        kind=kind,
        label=label,
        action_bias=action_bias,
        timestamp=fractal.timestamp if fractal is not None else None,
        price=round(fractal.price, 2) if fractal is not None else None,
        score=score,
        explanation=explanation,
        invalidation=invalidation,
    )


def classify_trade_point(structure: ChanStructure, latest_price: float) -> TradePoint:
    if not structure.strokes:
        return _empty_point()

    last_stroke = structure.strokes[-1]
    last_bottom = _last_fractal(structure, "bottom")
    last_top = _last_fractal(structure, "top")

    if structure.down_divergence_repair and last_bottom is not None:
        return _point(
            "first_buy",
            "一买",
            "buy",
            last_bottom,
            0.78,
            "下跌力度衰竭，最近底分型附近出现一买观察点，适合等待小级别向上确认。",
            f"跌破一买低点 {last_bottom.price:.2f}",
        )

    if structure.up_divergence_risk and last_top is not None:
        return _point(
            "first_sell",
            "一卖",
            "sell",
            last_top,
            0.76,
            "上涨力度衰竭，最近顶分型附近出现一卖风险点，适合降低追高和持仓风险。",
            f"重新放量突破一卖高点 {last_top.price:.2f}",
        )

    if len(structure.strokes) >= 3 and _last_three_directions(structure.strokes) == ["down", "up", "down"]:
        pullback_bottom = last_stroke.end if last_stroke.end.kind == "bottom" else last_bottom
        previous_bottom = (
            _previous_fractal_before(structure, "bottom", pullback_bottom.index)
            if pullback_bottom is not None
            else None
        )
        if pullback_bottom is not None and previous_bottom is not None and pullback_bottom.price > previous_bottom.price:
            return _point(
                "second_buy",
                "二买",
                "buy",
                pullback_bottom,
                0.72,
                "第一段反弹后回调不破前低，说明卖压减弱，形成二买观察点。",
                f"跌破二买回调低点 {pullback_bottom.price:.2f}",
            )

    if len(structure.strokes) >= 3 and _last_three_directions(structure.strokes) == ["up", "down", "up"]:
        rebound_top = last_stroke.end if last_stroke.end.kind == "top" else last_top
        previous_top = (
            _previous_fractal_before(structure, "top", rebound_top.index)
            if rebound_top is not None
            else None
        )
        if rebound_top is not None and previous_top is not None and rebound_top.price < previous_top.price:
            return _point(
                "second_sell",
                "二卖",
                "sell",
                rebound_top,
                0.72,
                "第一段下跌后反弹不过前高，说明买盘恢复不足，形成二卖风险点。",
                f"重新突破二卖反弹高点 {rebound_top.price:.2f}",
            )

    if structure.trend == "uptrend" and last_stroke.direction == "down" and last_bottom is not None:
        return _point(
            "third_buy",
            "三买",
            "buy",
            last_bottom,
            0.68,
            "上升趋势中的回踩未明显破坏结构，形成三买观察点。",
            f"跌破三买回踩低点 {last_bottom.price:.2f}",
        )

    if structure.trend == "downtrend" and last_stroke.direction == "up" and last_top is not None:
        return _point(
            "third_sell",
            "三卖",
            "sell",
            last_top,
            0.68,
            "下跌趋势中的反弹未明显扭转结构，形成三卖风险点。",
            f"重新突破三卖反弹高点 {last_top.price:.2f}",
        )

    return _empty_point()


def _favorable_return(sample: TradePointReplaySample, action_bias: str) -> float:
    if sample.entry_price <= 0:
        return 0.0
    if action_bias == "sell":
        return (sample.entry_price - sample.exit_price) / sample.entry_price * 100
    return (sample.exit_price - sample.entry_price) / sample.entry_price * 100


def summarize_replay_samples(
    kind: str,
    label: str,
    action_bias: str,
    horizon_days: int,
    samples: list[TradePointReplaySample],
) -> TradePointReplay:
    if not samples:
        return TradePointReplay(
            kind=kind,
            label=label,
            horizon_days=horizon_days,
            sample_count=0,
            favorable_count=0,
            favorable_rate=None,
            average_return_pct=None,
            best_return_pct=None,
            worst_return_pct=None,
            summary=f"近似复盘里暂未找到足够的{label}样本。",
        )

    returns = [_favorable_return(sample, action_bias) for sample in samples]
    favorable_count = sum(1 for item in returns if item > 0)
    favorable_rate = round(favorable_count / len(samples), 2)
    average_return = round(sum(returns) / len(returns), 2)
    best_return = round(max(returns), 2)
    worst_return = round(min(returns), 2)
    summary = (
        f"近{len(samples)}次{label}后{horizon_days}日，"
        f"有利走势{favorable_count}次，占比{favorable_rate:.0%}，"
        f"平均有利幅度{average_return:.2f}%。"
    )
    return TradePointReplay(
        kind=kind,
        label=label,
        horizon_days=horizon_days,
        sample_count=len(samples),
        favorable_count=favorable_count,
        favorable_rate=favorable_rate,
        average_return_pct=average_return,
        best_return_pct=best_return,
        worst_return_pct=worst_return,
        summary=summary,
    )


def replay_trade_points(
    rows: list[KLine],
    kind: str,
    label: str,
    action_bias: str,
    horizon_days: int = 5,
    lookback: int = 160,
    min_gap: int = 4,
) -> TradePointReplay:
    if kind == "none" or horizon_days <= 0:
        return summarize_replay_samples(kind, label, action_bias, horizon_days, [])

    samples: list[TradePointReplaySample] = []
    end = len(rows) - horizon_days
    if end <= 0:
        return summarize_replay_samples(kind, label, action_bias, horizon_days, [])

    start = max(0, end - lookback)
    previous_timestamp: str | None = None
    for index in range(start, end):
        prefix = rows[: index + 1]
        if len(prefix) < 7:
            continue
        structure = analyze_structure(prefix, min_gap=min_gap)
        point = classify_trade_point(structure, rows[index].close)
        if point.kind != kind or point.timestamp is None:
            continue
        if point.timestamp == previous_timestamp:
            continue
        previous_timestamp = point.timestamp
        samples.append(
            TradePointReplaySample(
                timestamp=rows[index].timestamp,
                entry_price=rows[index].close,
                exit_price=rows[index + horizon_days].close,
            )
        )

    return summarize_replay_samples(kind, label, action_bias, horizon_days, samples)
