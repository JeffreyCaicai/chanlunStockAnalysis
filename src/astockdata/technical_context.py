from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from .kline import KLine


@dataclass(frozen=True)
class TechnicalContext:
    label: str
    score: float
    momentum_label: str
    momentum_score: float
    ma20: float | None
    ma20_slope_pct: float | None
    roc5_pct: float | None
    bollinger_label: str
    bollinger_width_pct: float | None
    bollinger_width_percentile: float | None
    summary: str
    reasons: list[str]
    risk_notes: list[str]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    average = _mean(values)
    variance = sum((value - average) ** 2 for value in values) / len(values)
    return sqrt(variance)


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return (current - previous) / previous * 100


def _clamp(value: float, low: float = 0.05, high: float = 0.95) -> float:
    return max(low, min(high, value))


def _neutral_context(reason: str = "技术辅助数据不足，暂不参与信号判断。") -> TechnicalContext:
    return TechnicalContext(
        label="中性",
        score=0.5,
        momentum_label="数据不足",
        momentum_score=0.5,
        ma20=None,
        ma20_slope_pct=None,
        roc5_pct=None,
        bollinger_label="数据不足",
        bollinger_width_pct=None,
        bollinger_width_percentile=None,
        summary=reason,
        reasons=[reason],
        risk_notes=[],
    )


def _bollinger_widths(closes: list[float], window: int = 20) -> list[float]:
    widths: list[float] = []
    for index in range(window, len(closes) + 1):
        segment = closes[index - window : index]
        middle = _mean(segment)
        if middle <= 0:
            continue
        widths.append(4 * _std(segment) / middle * 100)
    return widths


def _percentile_rank(values: list[float], value: float) -> float:
    if not values:
        return 0.5
    below_or_equal = sum(1 for item in values if item <= value)
    return below_or_equal / len(values)


def build_technical_context(rows: list[KLine]) -> TechnicalContext:
    if len(rows) < 26:
        return _neutral_context()

    closes = [row.close for row in rows if row.close > 0]
    if len(closes) < 26:
        return _neutral_context()

    latest_close = closes[-1]
    ma20 = _mean(closes[-20:])
    previous_ma20 = _mean(closes[-25:-5])
    ma20_slope_pct = _pct_change(ma20, previous_ma20)
    roc5_pct = _pct_change(latest_close, closes[-6])

    momentum_score = 0.5
    if latest_close > ma20:
        momentum_score += 0.08
    elif latest_close < ma20:
        momentum_score -= 0.08
    if ma20_slope_pct > 0.3:
        momentum_score += 0.12
    elif ma20_slope_pct < -0.3:
        momentum_score -= 0.12
    if roc5_pct > 1.0:
        momentum_score += 0.12
    elif roc5_pct < -1.0:
        momentum_score -= 0.12
    momentum_score = round(_clamp(momentum_score), 2)

    if momentum_score >= 0.62:
        momentum_label = "动量向上"
        momentum_reason = f"短线走势偏强：最近5个交易日上涨{roc5_pct:.2f}%，收盘价在20日均线之上，说明近期买盘更主动"
    elif momentum_score <= 0.38:
        momentum_label = "动量走弱"
        momentum_reason = f"短线走势转弱：最近5个交易日下跌{abs(roc5_pct):.2f}%，收盘价在20日均线之下，说明近期卖压更明显"
    else:
        momentum_label = "动量中性"
        momentum_reason = f"短线走势一般：最近5个交易日变化{roc5_pct:.2f}%，20日均线变化不明显"

    widths = _bollinger_widths(closes)
    latest_width = widths[-1] if widths else None
    width_percentile = _percentile_rank(widths, latest_width) if latest_width is not None else None
    latest_std = _std(closes[-20:])
    upper = ma20 + latest_std * 2
    lower = ma20 - latest_std * 2
    bollinger_label = "数据不足"
    bollinger_reason = "布林带数据不足"

    if latest_width is not None and width_percentile is not None:
        is_compressed = width_percentile <= 0.3 or latest_width <= 6.0
        if is_compressed:
            if latest_close > upper:
                bollinger_label = "压缩后向上突破"
                bollinger_reason = f"从窄幅震荡向上突破：布林带宽约{latest_width:.2f}%，价格开始向上打开"
            elif latest_close < lower:
                bollinger_label = "压缩后向下突破"
                bollinger_reason = f"从窄幅震荡向下跌破：布林带宽约{latest_width:.2f}%，价格开始向下打开"
            else:
                bollinger_label = "布林压缩"
                bollinger_reason = f"波动正在收窄：布林带宽约{latest_width:.2f}%，表示价格越走越窄，通常需要等待方向选择"
        elif width_percentile >= 0.75:
            bollinger_label = "波动扩张"
            bollinger_reason = f"波动明显放大：布林带宽约{latest_width:.2f}%，表示最近20日上下波动空间很大，追涨时要防回撤"
        else:
            bollinger_label = "正常波动"
            bollinger_reason = f"波动处在常规范围：布林带宽约{latest_width:.2f}%，价格波动没有明显收窄或放大"

    score = 0.5
    if momentum_label == "动量向上":
        score += 0.15
    elif momentum_label == "动量走弱":
        score -= 0.15

    if bollinger_label == "压缩后向上突破":
        score += 0.08
    elif bollinger_label == "压缩后向下突破":
        score -= 0.08
    elif bollinger_label == "布林压缩":
        score += 0.02
    score = round(_clamp(score), 2)

    if momentum_label == "动量走弱" or bollinger_label == "压缩后向下突破":
        label = "拖累"
    elif momentum_label == "动量向上" or bollinger_label == "压缩后向上突破":
        label = "助力"
    elif bollinger_label == "布林压缩":
        label = "蓄势"
    else:
        label = "中性"

    reasons = [momentum_reason, bollinger_reason]
    if bollinger_label == "布林压缩":
        reasons.append("等待方向选择")
    risk_notes: list[str] = []
    if momentum_label == "动量走弱":
        risk_notes.append("趋势动量走弱")
    if bollinger_label == "压缩后向下突破":
        risk_notes.append("布林压缩后向下突破")

    return TechnicalContext(
        label=label,
        score=score,
        momentum_label=momentum_label,
        momentum_score=momentum_score,
        ma20=round(ma20, 2),
        ma20_slope_pct=round(ma20_slope_pct, 2),
        roc5_pct=round(roc5_pct, 2),
        bollinger_label=bollinger_label,
        bollinger_width_pct=round(latest_width, 2) if latest_width is not None else None,
        bollinger_width_percentile=round(width_percentile, 2) if width_percentile is not None else None,
        summary=f"{momentum_reason}；{bollinger_reason}",
        reasons=reasons,
        risk_notes=risk_notes,
    )
