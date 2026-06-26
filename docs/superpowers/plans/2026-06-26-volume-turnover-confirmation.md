# Volume Turnover Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add volume and optional turnover confirmation so buy/sell signals can explain whether price movement has enough trading participation behind it.

**Architecture:** Create a focused `volume_context.py` module that derives a `VolumeContext` from daily K-lines and optional current turnover. Pass this context through `ChanAnalyzer`, `ChanSignalEngine`, and backtest evaluation. Use it as auxiliary scoring and buy-veto input, then expose it in JSON, CLI tables, and the local Web UI.

**Tech Stack:** Python dataclasses, existing `unittest` suite, static HTML/JavaScript in `src/astockdata/web_static.py`.

---

### File Map

- Create `src/astockdata/volume_context.py`: volume/amount/turnover classification.
- Create `tests/test_volume_context.py`: isolated volume-context rules.
- Modify `src/astockdata/signals.py`: add `volume_context` to `ChanSignal`, adjust score/reasons, and pass to veto.
- Modify `src/astockdata/veto.py`: add volume-based hard and combined veto rules.
- Modify `tests/test_signals.py` and `tests/test_veto.py`: integration tests.
- Modify `src/astockdata/backtest.py`: pass `build_volume_context(history)` into signal evaluation.
- Modify `src/astockdata/chan_cli.py`: show volume context in table output.
- Modify `src/astockdata/web_static.py`: show volume context in single-stock panel and CSV result table.
- Modify `tests/test_chan_cli.py` and `tests/test_web.py`: display assertions.

### Task 1: Volume Context Model And Rules

**Files:**
- Create: `src/astockdata/volume_context.py`
- Create: `tests/test_volume_context.py`

- [ ] **Step 1: Write failing volume-context tests**

Create `tests/test_volume_context.py`:

```python
import unittest

from astockdata.kline import KLine
from astockdata.volume_context import build_volume_context


def kline(index, close, volume=100.0, amount=None):
    return KLine(
        "600519",
        "1d",
        f"2026-06-{index:02d}",
        close,
        close + 1,
        close - 1,
        close,
        float(volume),
        float(amount if amount is not None else volume * close),
    )


def base_rows():
    return [kline(index, 10 + index * 0.1, 100.0, 1000.0) for index in range(1, 22)]


class VolumeContextTests(unittest.TestCase):
    def test_volume_surge_up_supports_buy_confirmation(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 21.0, 160.0, 1800.0)

        context = build_volume_context(rows, turnover_pct=6.2)

        self.assertEqual(context.label, "助力")
        self.assertEqual(context.volume_label, "放量上涨")
        self.assertGreater(context.volume_ratio_5, 1.3)
        self.assertEqual(context.turnover_label, "换手活跃")
        self.assertIn("放量上涨", context.summary)

    def test_shrinking_volume_pullback_is_setup(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 19.0, 70.0, 700.0)

        context = build_volume_context(rows)

        self.assertEqual(context.label, "蓄势")
        self.assertEqual(context.volume_label, "缩量回调")
        self.assertIn("抛压不强", context.summary)

    def test_volume_surge_down_flags_risk(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 18.5, 170.0, 1800.0)

        context = build_volume_context(rows)

        self.assertEqual(context.label, "拖累")
        self.assertEqual(context.volume_label, "放量下跌")
        self.assertIn("放量下跌", context.risk_notes)

    def test_low_volume_rise_is_weak(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 21.0, 70.0, 760.0)

        context = build_volume_context(rows)

        self.assertEqual(context.label, "拖累")
        self.assertEqual(context.volume_label, "无量上涨")
        self.assertIn("成交量没有跟上", context.summary)

    def test_insufficient_rows_returns_neutral_context(self):
        context = build_volume_context(base_rows()[:10])

        self.assertEqual(context.label, "中性")
        self.assertEqual(context.volume_label, "数据不足")
        self.assertIn("量能数据不足", context.summary)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_volume_context -v
```

Expected: fail because `astockdata.volume_context` does not exist.

- [ ] **Step 3: Implement `volume_context.py`**

Create `VolumeContext` and `build_volume_context()`:

```python
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
    reasons: list[str] = []
    risk_notes: list[str] = []
    label = "中性"
    score = 0.5

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
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_volume_context -v
```

Expected: all `tests.test_volume_context` tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/astockdata/volume_context.py tests/test_volume_context.py
git commit -m "feat: add volume context"
```

### Task 2: Signal And Veto Integration

**Files:**
- Modify: `src/astockdata/signals.py`
- Modify: `src/astockdata/veto.py`
- Modify: `src/astockdata/backtest.py`
- Test: `tests/test_signals.py`
- Test: `tests/test_veto.py`

- [ ] **Step 1: Write failing integration tests**

In `tests/test_signals.py`, import `VolumeContext`, add helper:

```python
def volume_context(label, volume_label, summary):
    return VolumeContext(
        label=label,
        score=0.68 if label == "助力" else 0.28 if label == "拖累" else 0.5,
        volume_label=volume_label,
        volume_ratio_5=1.6 if "放量" in volume_label else 0.7,
        volume_ratio_20=1.4,
        amount_ratio_5=1.5,
        turnover_pct=None,
        turnover_label="数据不足",
        summary=summary,
        reasons=[summary],
        risk_notes=[volume_label] if label == "拖累" else [],
    )
```

Add tests:

```python
def test_supportive_volume_context_adds_reason_to_buy_signal(self):
    engine = ChanSignalEngine()

    signal = engine.evaluate(
        "600519",
        daily_structure=self.first_buy_structure(),
        confirm_structure=self.make_structure("uptrend"),
        latest_price=8.8,
        volume_context=volume_context("助力", "放量上涨", "放量上涨：买盘参与更主动"),
    )

    payload = signal.to_dict()
    self.assertEqual(payload["volume_context"]["label"], "助力")
    self.assertIn("量能确认偏正面", "；".join(signal.reasons))

def test_volume_surge_down_vetoes_buy_signal(self):
    engine = ChanSignalEngine()

    signal = engine.evaluate(
        "600519",
        daily_structure=self.first_buy_structure(),
        confirm_structure=self.make_structure("uptrend"),
        latest_price=8.8,
        volume_context=volume_context("拖累", "放量下跌", "放量下跌：抛压增强"),
    )

    self.assertEqual(signal.action, "继续持有")
    self.assertTrue(signal.veto_context.vetoed)
    self.assertIn("放量下跌", "；".join(signal.veto_context.reasons))
```

In `tests/test_veto.py`, import `VolumeContext`, add helper and a direct veto test:

```python
def volume(label, volume_label):
    return VolumeContext(label, 0.28 if label == "拖累" else 0.5, volume_label, 1.6, 1.4, 1.5, None, "数据不足", volume_label, [volume_label], [volume_label])

def test_vetoes_buy_when_volume_surge_down(self):
    veto = evaluate_buy_veto(
        signal="强买入",
        action="买入",
        latest_price=20.0,
        structure=structure(),
        trade_point=trade_point("first_buy", "一买"),
        confirmation_missing=False,
        volume_context=volume("拖累", "放量下跌"),
    )

    self.assertTrue(veto.vetoed)
    self.assertIn("放量下跌", "；".join(veto.reasons))
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_signals tests.test_veto -v
```

Expected: fail because `volume_context` is not accepted by `evaluate()` or veto.

- [ ] **Step 3: Wire volume context into signal engine**

In `signals.py`:

- Import `VolumeContext, build_volume_context`.
- Add `volume_context: VolumeContext | None = None` to `ChanSignal`.
- Add `volume_context: VolumeContext | None = None` argument to `ChanSignalEngine.evaluate()`.
- Before veto evaluation, apply:

```python
        if volume_context is not None:
            if volume_context.label == "助力" and map_signal_to_action(signal) == "买入":
                confidence = min(0.9, confidence + 0.04)
                reasons.append(f"量能确认偏正面：{volume_context.summary}")
            elif volume_context.label == "拖累" and map_signal_to_action(signal) == "买入":
                confidence = max(0.45, confidence - 0.08)
                risk_notes.append(f"量能确认偏负面：{volume_context.summary}")
            elif volume_context.label == "拖累" and map_signal_to_action(signal) == "卖出":
                confidence = min(0.9, confidence + 0.04)
                reasons.append(f"量能确认偏负面，卖出/减仓信号需要优先处理：{volume_context.summary}")
            elif volume_context.label == "蓄势":
                reasons.append(f"量能显示蓄势：{volume_context.summary}")
```

- Pass `volume_context=volume_context` into `ChanSignal`.
- In `ChanAnalyzer.analyze()`, call `build_volume_context(daily_rows)` and pass it to `evaluate()`.

In `backtest.py`, import `build_volume_context` and pass `volume_context=build_volume_context(history)`.

- [ ] **Step 4: Wire volume context into veto**

In `veto.py`:

- Import `VolumeContext`.
- Add `volume_context: VolumeContext | None = None` to `evaluate_buy_veto`.
- Add hard veto:

```python
    if volume_context and volume_context.volume_label == "放量下跌":
        hard.append("放量下跌，最新下跌伴随成交量明显放大，说明抛压增强")
```

- Add combined veto:

```python
    if confirmation_missing and volume_context and volume_context.volume_label == "无量上涨":
        combined.append("无量上涨叠加30分钟确认缺失，买入需要等待补量或小级别确认")
```

- In `signals.py`, pass `volume_context=volume_context` into `evaluate_buy_veto()`.

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_signals tests.test_veto -v
```

Expected: signal and veto tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/astockdata/signals.py src/astockdata/veto.py src/astockdata/backtest.py tests/test_signals.py tests/test_veto.py
git commit -m "feat: apply volume context to signals"
```

### Task 3: CLI And Web Display

**Files:**
- Modify: `src/astockdata/chan_cli.py`
- Modify: `src/astockdata/web_static.py`
- Test: `tests/test_chan_cli.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write failing display tests**

In `tests/test_chan_cli.py`, import `VolumeContext`, add to `sample_signal()`:

```python
volume_context=VolumeContext("助力", 0.68, "放量上涨", 1.6, 1.4, 1.5, None, "数据不足", "放量上涨：买盘参与更主动", ["放量上涨"], []),
```

In `test_render_table_contains_core_fields()`, add:

```python
self.assertIn("量能", output)
self.assertIn("放量上涨", output)
```

In `tests/test_web.py`, add:

```python
self.assertIn("量能换手", body)
self.assertIn('id="volumeContext"', body)
self.assertIn('id="volumeContextDetail"', body)
self.assertIn("volumeContextText", body)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli tests.test_web -v
```

Expected: fail because CLI/Web do not render volume context.

- [ ] **Step 3: Implement CLI display**

In `chan_cli.py`, add helper:

```python
def _volume_label(signal: ChanSignal) -> str:
    context = signal.volume_context
    if context is None:
        return "-"
    return context.volume_label or context.label
```

Add `量能` to headers after `辅助`, and `_volume_label(signal)` to rows.

- [ ] **Step 4: Implement Web display**

In `web_static.py`:

- Add KV row after auxiliary confirmation:

```html
<div class="kv"><span>量能换手</span><div class="strength-box"><strong id="volumeContext">-</strong><span id="volumeContextDetail" class="inline-hint">运行分析后显示成交量和换手状态</span></div></div>
```

- Add CSV table header `<th>量能</th>` after `辅助`.
- Add JS helpers:

```javascript
function volumeContextText(context) {
  if (!context) return "-";
  return context.volume_label || context.label || "-";
}

function volumeContextDetail(context) {
  if (!context) return "量能数据暂不可用。";
  return context.summary || "量能数据暂不可用。";
}
```

- In `renderPortfolio`, insert `volumeContextText(item.volume_context)` after technical context.
- In `renderSignal`, set `volumeContext` and `volumeContextDetail`.

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli tests.test_web -v
```

Expected: CLI and Web tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/astockdata/chan_cli.py src/astockdata/web_static.py tests/test_chan_cli.py tests/test_web.py
git commit -m "feat: show volume context"
```

### Task 4: Full Verification

**Files:**
- No new files

- [ ] **Step 1: Run all tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run CLI JSON smoke**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m astockdata.chan_cli 603337 --json
```

Expected: command exits with status 0 and JSON contains `volume_context`.

- [ ] **Step 3: Run backtest smoke**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m astockdata.chan_cli --backtest 603337 --horizons 5 --lookback 80
```

Expected: command exits with status 0 and prints backtest summary sections.

- [ ] **Step 4: Review status**

Run:

```bash
git status --short --branch
git log --oneline --decorate -8
```

Expected: branch is ahead of remote by this stage's commits, and only `.DS_Store` remains untracked.
