from __future__ import annotations

from dataclasses import asdict, dataclass

from .chan import CentralZone, ChanStructure, Fractal, Stroke
from .chan import analyze_structure
from .chan_points import TradePoint, TradePointReplay, classify_trade_point, replay_trade_points
from .kline import BaiduDailyKLineProvider, KLine, KLineProvider, MootdxKLineProvider
from .market_context import HttpMarketContextProvider, MarketContext, MarketContextProvider
from .resolver import EastmoneyStockResolver, StockResolver
from .technical_context import TechnicalContext, build_technical_context


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
class CentralZoneSummary:
    start_timestamp: str
    end_timestamp: str
    low: float
    high: float
    stroke_count: int
    direction: str
    position_label: str
    meaning: str


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
    latest_zone: CentralZoneSummary | None
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
    trade_point: TradePoint | None = None
    trade_point_replay: TradePointReplay | None = None
    market_context: MarketContext | None = None
    technical_context: TechnicalContext | None = None
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


def _zone_position(zone: CentralZone, latest_price: float | None) -> str:
    if latest_price is None:
        return zone.direction
    if latest_price > zone.high:
        return "up"
    if latest_price < zone.low:
        return "down"
    return "inside"


def _zone_position_label(position: str) -> str:
    labels = {"up": "中枢上方", "down": "中枢下方", "inside": "中枢内部"}
    return labels.get(position, "中枢内部")


def _zone_meaning(position: str) -> str:
    if position == "up":
        return "价格已经脱离中枢上方，后续重点看回踩是否跌回中枢。"
    if position == "down":
        return "价格已经脱离中枢下方，后续重点看反抽是否重新回到中枢。"
    return "价格仍在中枢内部震荡，方向还需要等待离开中枢后确认。"


def _central_zone_summary(zone: CentralZone | None, latest_price: float | None = None) -> CentralZoneSummary | None:
    if zone is None:
        return None
    position = _zone_position(zone, latest_price)
    return CentralZoneSummary(
        start_timestamp=zone.start_timestamp,
        end_timestamp=zone.end_timestamp,
        low=round(zone.low, 2),
        high=round(zone.high, 2),
        stroke_count=zone.stroke_count,
        direction=zone.direction,
        position_label=_zone_position_label(position),
        meaning=_zone_meaning(position),
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
        latest_zone=_central_zone_summary(structure.zones[-1] if structure.zones else None, latest_price),
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
        market_context: MarketContext | None = None,
        technical_context: TechnicalContext | None = None,
    ) -> ChanSignal:
        confirmation_missing = confirm_structure is None
        reasons: list[str] = []
        invalidations: list[str] = []
        risk_notes: list[str] = []
        confidence = 0.5
        trade_point = classify_trade_point(daily_structure, latest_price)
        trade_point_replay = replay_trade_points(
            recent_klines or [],
            kind=trade_point.kind,
            label=trade_point.label,
            action_bias=trade_point.action_bias,
        )

        if daily_structure.fractals:
            last_bottoms = [fractal for fractal in daily_structure.fractals if fractal.kind == "bottom"]
            if last_bottoms:
                invalidations.append(f"跌破最近日线底分型低点 {last_bottoms[-1].price:.2f}")

        if daily_structure.trend == "downtrend" and position and trade_point.action_bias != "buy":
            signal = "清仓卖出"
            confidence = 0.76
            reasons.append("日线结构处于下跌趋势")
            if position and latest_price < position.cost:
                risk_notes.append("跌破持仓成本，结构和成本风控同时转弱")
        elif trade_point.action_bias == "buy":
            signal = "强买入" if not confirmation_missing else "试买入"
            confidence = max(0.62, min(0.82, trade_point.score))
            reasons.append(f"缠论买卖点：{trade_point.label}，{trade_point.explanation}")
            if trade_point.invalidation != "-":
                invalidations.append(trade_point.invalidation)
        elif trade_point.action_bias == "sell" and position:
            signal = "减仓"
            confidence = max(0.62, min(0.82, trade_point.score))
            reasons.append(f"缠论买卖点：{trade_point.label}，{trade_point.explanation}")
            risk_notes.append(trade_point.invalidation)
        elif daily_structure.trend == "downtrend":
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
        if market_context is not None:
            if market_context.label == "顺风" and map_signal_to_action(signal) == "买入":
                confidence = min(0.9, confidence + 0.04)
                reasons.append(f"市场环境顺风：{market_context.summary}")
            elif market_context.label == "逆风" and map_signal_to_action(signal) == "买入":
                confidence = max(0.45, confidence - 0.1)
                risk_notes.append(f"市场环境逆风：{market_context.summary}")
            elif market_context.label == "逆风" and map_signal_to_action(signal) == "卖出":
                confidence = min(0.9, confidence + 0.04)
                reasons.append(f"市场环境逆风，卖出/减仓信号需要优先处理：{market_context.summary}")
        if technical_context is not None:
            if technical_context.label == "助力" and map_signal_to_action(signal) == "买入":
                confidence = min(0.9, confidence + 0.04)
                reasons.append(f"辅助确认偏正面：{technical_context.summary}")
            elif technical_context.label == "拖累" and map_signal_to_action(signal) == "买入":
                confidence = max(0.45, confidence - 0.08)
                risk_notes.append(f"辅助确认偏负面：{technical_context.summary}")
            elif technical_context.label == "拖累" and map_signal_to_action(signal) == "卖出":
                confidence = min(0.9, confidence + 0.04)
                reasons.append(f"辅助确认偏负面，卖出/减仓信号需要优先处理：{technical_context.summary}")
            elif technical_context.label == "蓄势":
                reasons.append(f"辅助确认显示蓄势：{technical_context.summary}")

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
            trade_point=trade_point,
            trade_point_replay=trade_point_replay,
            market_context=market_context,
            technical_context=technical_context,
            position_context=position,
        )


class ChanAnalyzer:
    def __init__(
        self,
        kline_provider: KLineProvider | None = None,
        confirm_provider: KLineProvider | None = None,
        engine: ChanSignalEngine | None = None,
        resolver: StockResolver | None = None,
        market_context_provider: MarketContextProvider | None = None,
    ):
        self.kline_provider = kline_provider or BaiduDailyKLineProvider()
        self.confirm_provider = confirm_provider or MootdxKLineProvider()
        self.engine = engine or ChanSignalEngine()
        self.resolver = resolver or EastmoneyStockResolver()
        self.market_context_provider = market_context_provider or HttpMarketContextProvider()

    def analyze(self, code: str, position: Position | None = None, intraday: bool = False) -> ChanSignal:
        identity = self.resolver.resolve(code)
        code = identity.code
        daily_rows = self.kline_provider.daily_klines(code)
        if not daily_rows:
            raise RuntimeError(f"No daily K-line data returned for {code}")
        confirm_rows = self.confirm_provider.intraday_klines(code, "30m")
        daily_structure = analyze_structure(daily_rows)
        confirm_structure = analyze_structure(confirm_rows, min_gap=2) if confirm_rows else None
        market_context = self.market_context_provider.context_for(code)
        technical_context = build_technical_context(daily_rows)
        return self.engine.evaluate(
            code=code,
            daily_structure=daily_structure,
            confirm_structure=confirm_structure,
            latest_price=daily_rows[-1].close,
            position=position,
            intraday=intraday,
            recent_klines=daily_rows,
            stock_name=identity.name,
            market_context=market_context,
            technical_context=technical_context,
        )
