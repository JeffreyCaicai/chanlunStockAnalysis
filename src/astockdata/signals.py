from __future__ import annotations

from dataclasses import asdict, dataclass

from .chan import ChanStructure, Fractal, Stroke
from .chan import analyze_structure
from .kline import BaiduDailyKLineProvider, KLine, KLineProvider, MootdxKLineProvider
from .resolver import EastmoneyStockResolver, StockResolver


@dataclass(frozen=True)
class Position:
    cost: float
    position: float


@dataclass(frozen=True)
class PricePoint:
    timestamp: str
    price: float


@dataclass(frozen=True)
class StrokePoint:
    direction: str
    direction_label: str
    start_timestamp: str
    end_timestamp: str
    start_price: float
    end_price: float
    amplitude: float


@dataclass(frozen=True)
class CandlePoint:
    timestamp: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class StructureSummary:
    trend: str
    trend_label: str
    latest_timestamp: str | None
    latest_price: float | None
    merged_count: int
    fractal_count: int
    stroke_count: int
    latest_top: PricePoint | None
    latest_bottom: PricePoint | None
    latest_stroke: StrokePoint | None
    up_divergence_risk: bool
    down_divergence_repair: bool
    source: str = ""


@dataclass(frozen=True)
class ChanSignal:
    code: str
    action: str
    signal: str
    confidence: float
    confirmed: bool
    intraday: bool
    confirmation_missing: bool
    reasons: list[str]
    invalidations: list[str]
    risk_notes: list[str]
    stock_name: str = ""
    strength_label: str = ""
    confirmation_status: str = ""
    daily_summary: StructureSummary | None = None
    confirmation_summary: StructureSummary | None = None
    recent_klines: list[CandlePoint] | None = None
    position_context: Position | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def map_signal_to_action(signal: str) -> str:
    if signal in {"强买入", "试买入"}:
        return "买入"
    if signal in {"减仓", "清仓卖出"}:
        return "卖出"
    return "继续持有"


def strength_label(confidence: float) -> str:
    if confidence >= 0.72:
        return "较强"
    if confidence >= 0.6:
        return "一般"
    return "偏弱"


def _trend_label(trend: str) -> str:
    labels = {
        "uptrend": "上升趋势",
        "downtrend": "下跌趋势",
        "range": "震荡整理",
        "unknown": "尚未成型",
    }
    return labels.get(trend, trend)


def _latest_fractal(fractals: list[Fractal], kind: str) -> PricePoint | None:
    selected = [fractal for fractal in fractals if fractal.kind == kind]
    if not selected:
        return None
    fractal = selected[-1]
    return PricePoint(fractal.timestamp, round(fractal.price, 2))


def _stroke_point(stroke: Stroke | None) -> StrokePoint | None:
    if stroke is None:
        return None
    direction_label = "向上笔" if stroke.direction == "up" else "向下笔"
    return StrokePoint(
        direction=stroke.direction,
        direction_label=direction_label,
        start_timestamp=stroke.start.timestamp,
        end_timestamp=stroke.end.timestamp,
        start_price=round(stroke.start.price, 2),
        end_price=round(stroke.end.price, 2),
        amplitude=round(stroke.amplitude, 2),
    )


def summarize_structure(
    structure: ChanStructure,
    latest_price: float | None = None,
    source: str = "",
) -> StructureSummary:
    latest_timestamp = structure.merged[-1].timestamp if structure.merged else None
    if latest_price is None and structure.merged:
        latest_price = structure.merged[-1].close
    return StructureSummary(
        trend=structure.trend,
        trend_label=_trend_label(structure.trend),
        latest_timestamp=latest_timestamp,
        latest_price=round(latest_price, 2) if latest_price is not None else None,
        merged_count=len(structure.merged),
        fractal_count=len(structure.fractals),
        stroke_count=len(structure.strokes),
        latest_top=_latest_fractal(structure.fractals, "top"),
        latest_bottom=_latest_fractal(structure.fractals, "bottom"),
        latest_stroke=_stroke_point(structure.strokes[-1] if structure.strokes else None),
        up_divergence_risk=structure.up_divergence_risk,
        down_divergence_repair=structure.down_divergence_repair,
        source=source,
    )


def confirmation_status(confirm_structure: ChanStructure | None) -> str:
    if confirm_structure is None:
        return "缺失"
    if confirm_structure.trend == "unknown":
        return "结构不足"
    return "有效确认"


def recent_candles(rows: list[KLine], limit: int = 40) -> list[CandlePoint]:
    return [
        CandlePoint(
            timestamp=row.timestamp,
            open=round(row.open, 2),
            high=round(row.high, 2),
            low=round(row.low, 2),
            close=round(row.close, 2),
        )
        for row in rows[-limit:]
    ]


class ChanSignalEngine:
    def evaluate(
        self,
        code: str,
        daily_structure: ChanStructure,
        confirm_structure: ChanStructure | None,
        latest_price: float,
        position: Position | None = None,
        intraday: bool = False,
        daily_source: str = "baidu_http",
        confirm_source: str = "mootdx_30m",
        recent_klines: list[KLine] | None = None,
        stock_name: str = "",
    ) -> ChanSignal:
        confirmation_missing = confirm_structure is None
        reasons: list[str] = []
        invalidations: list[str] = []
        risk_notes: list[str] = []
        confidence = 0.5

        if daily_structure.fractals:
            last_bottoms = [fractal for fractal in daily_structure.fractals if fractal.kind == "bottom"]
            if last_bottoms:
                invalidations.append(f"跌破最近日线底分型低点 {last_bottoms[-1].price:.2f}")

        if daily_structure.trend == "downtrend":
            signal = "清仓卖出" if position else "观察"
            confidence = 0.76 if position else 0.55
            reasons.append("日线结构处于下跌趋势")
            if position and latest_price < position.cost:
                risk_notes.append("跌破持仓成本，结构和成本风控同时转弱")
        elif daily_structure.trend == "uptrend" and not daily_structure.up_divergence_risk:
            if confirmation_missing:
                signal = "试买入"
                confidence = 0.62
                reasons.append("日线结构偏强，但缺少30分钟确认")
            else:
                signal = "强买入"
                confidence = 0.78
                reasons.append("日线结构偏强，30分钟确认可用")
        elif position and daily_structure.up_divergence_risk:
            signal = "减仓"
            confidence = 0.68
            reasons.append("日线存在上行背驰风险")
        elif position:
            signal = "持有"
            confidence = 0.64
            reasons.append("日线结构未明显破坏")
        else:
            signal = "观察"
            confidence = 0.5
            reasons.append("结构信号不足，等待更明确买卖点")

        if confirmation_missing:
            reasons.append("30分钟确认数据不可用，信号降级")
            confidence = min(confidence, 0.66)
        if intraday:
            reasons.append("盘中预警基于未完成K线，正式信号需收盘确认")
            confidence = min(confidence, 0.6)

        return ChanSignal(
            code=code,
            stock_name=stock_name,
            action=map_signal_to_action(signal),
            signal=signal,
            confidence=round(confidence, 2),
            confirmed=not intraday,
            intraday=intraday,
            confirmation_missing=confirmation_missing,
            reasons=reasons,
            invalidations=invalidations,
            risk_notes=risk_notes,
            strength_label=strength_label(confidence),
            confirmation_status=confirmation_status(confirm_structure),
            daily_summary=summarize_structure(daily_structure, latest_price, daily_source),
            confirmation_summary=(
                summarize_structure(confirm_structure, source=confirm_source)
                if confirm_structure is not None
                else None
            ),
            recent_klines=recent_candles(recent_klines or []),
            position_context=position,
        )


class ChanAnalyzer:
    def __init__(
        self,
        kline_provider: KLineProvider | None = None,
        confirm_provider: KLineProvider | None = None,
        engine: ChanSignalEngine | None = None,
        resolver: StockResolver | None = None,
    ):
        self.kline_provider = kline_provider or BaiduDailyKLineProvider()
        self.confirm_provider = confirm_provider or MootdxKLineProvider()
        self.engine = engine or ChanSignalEngine()
        self.resolver = resolver or EastmoneyStockResolver()

    def analyze(self, code: str, position: Position | None = None, intraday: bool = False) -> ChanSignal:
        identity = self.resolver.resolve(code)
        code = identity.code
        daily_rows = self.kline_provider.daily_klines(code)
        if not daily_rows:
            raise RuntimeError(f"No daily K-line data returned for {code}")
        confirm_rows = self.confirm_provider.intraday_klines(code, "30m")
        daily_structure = analyze_structure(daily_rows)
        confirm_structure = analyze_structure(confirm_rows, min_gap=2) if confirm_rows else None
        return self.engine.evaluate(
            code=code,
            daily_structure=daily_structure,
            confirm_structure=confirm_structure,
            latest_price=daily_rows[-1].close,
            position=position,
            intraday=intraday,
            recent_klines=daily_rows,
            stock_name=identity.name,
        )
