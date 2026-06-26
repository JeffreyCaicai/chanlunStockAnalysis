from __future__ import annotations

from dataclasses import dataclass

from .kline import KLine


@dataclass(frozen=True)
class VolumeContext:
    label: str
    score: float
    volume_label: str
    volume_ratio_5: float | None
    volume_ratio_20: float | None
    amount_ratio_5: float | None
    turnover_pct: float | None
    turnover_label: str
    summary: str
    reasons: list[str]
    risk_notes: list[str]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _ratio(value: float, base: float) -> float | None:
    if base <= 0:
        return None
    return round(value / base, 2)


def _turnover_label(turnover_pct: float | None) -> str:
    if turnover_pct is None:
        return "数据不足"
    if turnover_pct < 1.0:
        return "换手不足"
    if turnover_pct <= 5.0:
        return "换手温和"
    return "换手活跃"


def _neutral(reason: str = "量能数据不足，暂不参与信号判断。") -> VolumeContext:
    return VolumeContext(
        label="中性",
        score=0.5,
        volume_label="数据不足",
        volume_ratio_5=None,
        volume_ratio_20=None,
        amount_ratio_5=None,
        turnover_pct=None,
        turnover_label="数据不足",
        summary=reason,
        reasons=[reason],
        risk_notes=[],
    )


def build_volume_context(rows: list[KLine], turnover_pct: float | None = None) -> VolumeContext:
    if len(rows) < 21:
        return _neutral()

    latest = rows[-1]
    previous = rows[-2]
    recent_5 = rows[-6:-1]
    recent_20 = rows[-21:-1]
    avg_volume_5 = _mean([row.volume for row in recent_5 if row.volume > 0])
    avg_volume_20 = _mean([row.volume for row in recent_20 if row.volume > 0])
    avg_amount_5 = _mean([row.amount for row in recent_5 if row.amount > 0])
    volume_ratio_5 = _ratio(latest.volume, avg_volume_5)
    volume_ratio_20 = _ratio(latest.volume, avg_volume_20)
    amount_ratio_5 = _ratio(latest.amount, avg_amount_5)
    turnover_label = _turnover_label(turnover_pct)

    if volume_ratio_5 is None:
        return _neutral()

    price_up = latest.close > previous.close
    price_down = latest.close < previous.close
    high_volume = volume_ratio_5 >= 1.3
    low_volume = volume_ratio_5 <= 0.85
    label = "中性"
    score = 0.5
    reasons: list[str] = []
    risk_notes: list[str] = []

    if price_up and high_volume:
        volume_label = "放量上涨"
        label = "助力"
        score = 0.68
        reasons.append(f"放量上涨：成交量约为5日均量的{volume_ratio_5:.2f}倍，买盘参与更主动")
    elif price_down and low_volume:
        volume_label = "缩量回调"
        label = "蓄势"
        score = 0.58
        reasons.append(f"缩量回调：成交量约为5日均量的{volume_ratio_5:.2f}倍，说明回落时抛压不强")
    elif price_down and high_volume:
        volume_label = "放量下跌"
        label = "拖累"
        score = 0.28
        reasons.append(f"放量下跌：成交量约为5日均量的{volume_ratio_5:.2f}倍，说明抛压增强")
        risk_notes.append("放量下跌")
    elif price_up and low_volume:
        volume_label = "无量上涨"
        label = "拖累"
        score = 0.36
        reasons.append(f"无量上涨：价格上涨但成交量只有5日均量的{volume_ratio_5:.2f}倍，成交量没有跟上")
        risk_notes.append("无量上涨")
    else:
        volume_label = "量能平稳"
        reasons.append(f"量能平稳：成交量约为5日均量的{volume_ratio_5:.2f}倍")

    if amount_ratio_5 is not None:
        if amount_ratio_5 >= 1.2:
            reasons.append(f"成交额同步放大：约为5日均额的{amount_ratio_5:.2f}倍")
        elif amount_ratio_5 <= 0.85:
            reasons.append(f"成交额偏低：约为5日均额的{amount_ratio_5:.2f}倍")
    if turnover_label != "数据不足":
        reasons.append(f"当前换手率{turnover_pct:.2f}%，{turnover_label}")
        if turnover_label == "换手不足" and label == "助力":
            score = max(0.5, score - 0.08)

    summary = "；".join(reasons)
    return VolumeContext(
        label=label,
        score=round(score, 2),
        volume_label=volume_label,
        volume_ratio_5=volume_ratio_5,
        volume_ratio_20=volume_ratio_20,
        amount_ratio_5=amount_ratio_5,
        turnover_pct=turnover_pct,
        turnover_label=turnover_label,
        summary=summary,
        reasons=reasons,
        risk_notes=risk_notes,
    )
