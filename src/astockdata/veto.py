from __future__ import annotations

from dataclasses import dataclass

from .chan import ChanStructure
from .chan_points import TradePoint
from .market_context import MarketContext
from .technical_context import TechnicalContext


@dataclass(frozen=True)
class VetoContext:
    vetoed: bool
    level: str
    summary: str
    reasons: list[str]
    original_signal: str
    original_action: str


def _empty(signal: str, action: str) -> VetoContext:
    return VetoContext(False, "none", "未触发买入否决条件。", [], signal, action)


def _triggered(level: str, reasons: list[str], signal: str, action: str) -> VetoContext:
    prefix = "买入被否决" if level == "hard" else "买入暂缓"
    return VetoContext(True, level, f"{prefix}：{reasons[0]}", reasons, signal, action)


def _invalidation_triggered(invalidation: str, latest_price: float) -> bool:
    if not invalidation or invalidation == "-":
        return False
    numbers: list[float] = []
    for part in invalidation.replace("，", " ").split():
        try:
            numbers.append(float(part))
        except ValueError:
            continue
    if not numbers:
        return False
    target = numbers[-1]
    if "跌" in invalidation or "破" in invalidation:
        return latest_price <= target
    return latest_price >= target


def evaluate_buy_veto(
    *,
    signal: str,
    action: str,
    latest_price: float,
    structure: ChanStructure,
    trade_point: TradePoint | None,
    confirmation_missing: bool,
    market_context: MarketContext | None = None,
    technical_context: TechnicalContext | None = None,
) -> VetoContext:
    if action != "买入":
        return _empty(signal, action)

    hard: list[str] = []
    combined: list[str] = []
    zone = structure.zones[-1] if structure.zones else None

    if trade_point and trade_point.kind == "third_buy" and zone is not None and latest_price <= zone.high:
        hard.append(f"三买后价格重新回到中枢，当前价 {latest_price:.2f} 未站上中枢上沿 {zone.high:.2f}")
    if technical_context and technical_context.bollinger_label == "压缩后向下突破":
        hard.append("布林压缩后向下突破，价格从窄幅震荡向下选择方向")
    if structure.trend == "downtrend" and (trade_point is None or trade_point.kind not in {"first_buy", "second_buy"}):
        hard.append("日线仍是下跌趋势，且没有一买或二买修复结构")
    if trade_point and _invalidation_triggered(trade_point.invalidation, latest_price):
        hard.append(f"买点失效条件已触发：{trade_point.invalidation}")
    if hard:
        return _triggered("hard", hard, signal, action)

    if market_context and market_context.label == "逆风" and technical_context and technical_context.label == "拖累":
        combined.append("市场逆风叠加技术拖累，买入胜率需要重新确认")
    if confirmation_missing and technical_context and technical_context.label == "拖累":
        combined.append("30分钟确认缺失且技术辅助偏负面")
    if zone is not None and zone.low <= latest_price <= zone.high and (trade_point is None or trade_point.kind == "none"):
        combined.append("价格仍在中枢内部震荡，尚未离开中枢形成明确买点")
    if combined:
        return _triggered("combined", combined, signal, action)

    return _empty(signal, action)
