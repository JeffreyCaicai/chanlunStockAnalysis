from __future__ import annotations

from dataclasses import dataclass

from .kline import KLine


@dataclass(frozen=True)
class MergedKLine:
    code: str
    period: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    source_indices: list[int]


@dataclass(frozen=True)
class Fractal:
    kind: str
    timestamp: str
    price: float
    index: int


@dataclass(frozen=True)
class Stroke:
    start: Fractal
    end: Fractal
    direction: str
    amplitude: float
    volume: float


@dataclass(frozen=True)
class ChanStructure:
    merged: list[MergedKLine]
    fractals: list[Fractal]
    strokes: list[Stroke]
    trend: str
    up_divergence_risk: bool
    down_divergence_repair: bool


def _to_merged(row: KLine, index: int) -> MergedKLine:
    return MergedKLine(
        code=row.code,
        period=row.period,
        timestamp=row.timestamp,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        amount=row.amount,
        source_indices=[index],
    )


def _contains(a: MergedKLine, b: MergedKLine) -> bool:
    return (a.high >= b.high and a.low <= b.low) or (b.high >= a.high and b.low <= a.low)


def merge_inclusions(rows: list[KLine]) -> list[MergedKLine]:
    merged: list[MergedKLine] = []
    direction = "up"
    for index, row in enumerate(rows):
        current = _to_merged(row, index)
        if not merged:
            merged.append(current)
            continue
        previous = merged[-1]
        if not _contains(previous, current):
            if current.high > previous.high and current.low > previous.low:
                direction = "up"
            elif current.high < previous.high and current.low < previous.low:
                direction = "down"
            merged.append(current)
            continue
        if direction == "up":
            high = max(previous.high, current.high)
            low = max(previous.low, current.low)
        else:
            high = min(previous.high, current.high)
            low = min(previous.low, current.low)
        merged[-1] = MergedKLine(
            code=previous.code,
            period=previous.period,
            timestamp=current.timestamp,
            open=previous.open,
            high=high,
            low=low,
            close=current.close,
            volume=previous.volume + current.volume,
            amount=previous.amount + current.amount,
            source_indices=previous.source_indices + current.source_indices,
        )
    return merged


def detect_fractals(rows: list[MergedKLine]) -> list[Fractal]:
    fractals: list[Fractal] = []
    for index in range(1, len(rows) - 1):
        left, middle, right = rows[index - 1], rows[index], rows[index + 1]
        if middle.high > left.high and middle.high > right.high and middle.low > left.low and middle.low > right.low:
            fractals.append(Fractal("top", middle.timestamp, middle.high, index))
        elif middle.low < left.low and middle.low < right.low and middle.high < left.high and middle.high < right.high:
            fractals.append(Fractal("bottom", middle.timestamp, middle.low, index))
    return fractals


def _more_extreme(candidate: Fractal, current: Fractal) -> bool:
    if candidate.kind == "top":
        return candidate.price > current.price
    return candidate.price < current.price


def _filtered_fractals(fractals: list[Fractal], min_gap: int) -> list[Fractal]:
    selected: list[Fractal] = []
    for fractal in fractals:
        if not selected:
            selected.append(fractal)
            continue
        last = selected[-1]
        if fractal.kind == last.kind:
            if _more_extreme(fractal, last):
                selected[-1] = fractal
            continue
        if fractal.index - last.index < min_gap:
            continue
        selected.append(fractal)
    return selected


def build_strokes(fractals: list[Fractal], min_gap: int = 4) -> list[Stroke]:
    selected = _filtered_fractals(fractals, min_gap)
    strokes: list[Stroke] = []
    for start, end in zip(selected, selected[1:]):
        direction = "up" if start.kind == "bottom" and end.kind == "top" else "down"
        strokes.append(
            Stroke(
                start=start,
                end=end,
                direction=direction,
                amplitude=abs(end.price - start.price),
                volume=0.0,
            )
        )
    return strokes


def classify_trend(strokes: list[Stroke]) -> str:
    if len(strokes) < 2:
        return "unknown"
    highs = [stroke.end.price for stroke in strokes if stroke.end.kind == "top"]
    lows = [stroke.end.price for stroke in strokes if stroke.end.kind == "bottom"]
    if len(highs) >= 2 and len(lows) >= 1 and highs[-1] > highs[-2]:
        return "uptrend"
    if len(lows) >= 2 and len(highs) >= 1 and lows[-1] < lows[-2]:
        return "downtrend"
    return "range"


def _divergence(strokes: list[Stroke], direction: str) -> bool:
    same = [stroke for stroke in strokes if stroke.direction == direction]
    if len(same) < 2:
        return False
    previous, current = same[-2], same[-1]
    return current.amplitude < previous.amplitude


def analyze_structure(rows: list[KLine], min_gap: int = 4) -> ChanStructure:
    merged = merge_inclusions(rows)
    fractals = detect_fractals(merged)
    strokes = build_strokes(fractals, min_gap=min_gap)
    return ChanStructure(
        merged=merged,
        fractals=fractals,
        strokes=strokes,
        trend=classify_trend(strokes),
        up_divergence_risk=_divergence(strokes, "up"),
        down_divergence_repair=_divergence(strokes, "down"),
    )

