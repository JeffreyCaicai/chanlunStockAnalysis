# Buy Veto Conditions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add buy-side veto conditions that turn risky buy signals into observe signals while explaining why the original buy idea was rejected.

**Architecture:** Add a focused `src/astockdata/veto.py` module that evaluates structure, market, technical, and confirmation risks into a `VetoContext`. Wire it into `ChanSignalEngine.evaluate()` after the existing signal is produced so current buy-point logic remains visible. Display the veto context in CLI, JSON, and the local Web UI.

**Tech Stack:** Python dataclasses, existing `unittest` suite, static HTML/JavaScript in `src/astockdata/web_static.py`.

---

### File Map

- Create `src/astockdata/veto.py`: `VetoContext`, original signal metadata, and buy-veto rule evaluation.
- Create `tests/test_veto.py`: isolated rule tests with small fake structures and contexts.
- Modify `src/astockdata/signals.py`: add `veto_context` to `ChanSignal`, call veto evaluation, and rewrite buy signals when vetoed.
- Modify `tests/test_signals.py`: integration tests for signal rewriting and non-buy preservation.
- Modify `src/astockdata/chan_cli.py`: add veto column to table output.
- Modify `src/astockdata/web_static.py`: add single-stock and CSV-list veto display.
- Modify `tests/test_chan_cli.py` and `tests/test_web.py`: assert the new user-facing fields exist.

### Task 1: Veto Model And Rule Evaluation

**Files:**
- Create: `src/astockdata/veto.py`
- Create: `tests/test_veto.py`

- [ ] **Step 1: Write failing isolated veto tests**

Create `tests/test_veto.py` with tests for hard and combined veto rules:

```python
import unittest

from astockdata.chan import CentralZone, ChanStructure, Fractal, Stroke
from astockdata.chan_points import TradePoint
from astockdata.market_context import MarketContext
from astockdata.technical_context import TechnicalContext
from astockdata.veto import evaluate_buy_veto


def fractal(kind, ts, price, index):
    return Fractal(kind, ts, float(price), index)


def stroke(start, end):
    direction = "up" if start.kind == "bottom" and end.kind == "top" else "down"
    return Stroke(start, end, direction, abs(end.price - start.price), 100.0)


def structure(trend="uptrend", zone=None):
    bottom = fractal("bottom", "1", 10, 1)
    top = fractal("top", "2", 20, 5)
    return ChanStructure(
        merged=[],
        fractals=[bottom, top],
        strokes=[stroke(bottom, top)],
        zones=[zone] if zone else [],
        trend=trend,
        up_divergence_risk=False,
        down_divergence_repair=False,
    )


def trade_point(kind="third_buy", label="三买", invalidation="-"):
    return TradePoint(kind, label, "buy", "2", 20.0, 0.74, "买点候选", invalidation)


def market(label):
    return MarketContext(label, 0.3 if label == "逆风" else 0.5, None, "", None, label, [label], [])


def technical(label, bollinger="正常波动"):
    return TechnicalContext(
        label=label,
        score=0.3 if label == "拖累" else 0.5,
        momentum_label="动量走弱" if label == "拖累" else "动量中性",
        momentum_score=0.3 if label == "拖累" else 0.5,
        ma20=None,
        ma20_slope_pct=None,
        roc5_pct=None,
        bollinger_label=bollinger,
        bollinger_width_pct=None,
        bollinger_width_percentile=None,
        summary=label,
        reasons=[label],
        risk_notes=[],
    )


class BuyVetoTests(unittest.TestCase):
    def test_vetoes_third_buy_when_price_falls_back_into_zone(self):
        zone = CentralZone("1", "3", 12.0, 18.0, 3, "up")

        veto = evaluate_buy_veto(
            signal="强买入",
            action="买入",
            latest_price=15.0,
            structure=structure(zone=zone),
            trade_point=trade_point(),
            confirmation_missing=False,
        )

        self.assertTrue(veto.vetoed)
        self.assertEqual(veto.level, "hard")
        self.assertIn("三买后价格重新回到中枢", veto.summary)

    def test_vetoes_downward_bollinger_breakout(self):
        veto = evaluate_buy_veto(
            signal="强买入",
            action="买入",
            latest_price=20.0,
            structure=structure(),
            trade_point=trade_point("first_buy", "一买"),
            confirmation_missing=False,
            technical_context=technical("拖累", "压缩后向下突破"),
        )

        self.assertTrue(veto.vetoed)
        self.assertEqual(veto.level, "hard")
        self.assertIn("布林压缩后向下突破", "；".join(veto.reasons))

    def test_combines_market_headwind_and_technical_drag(self):
        veto = evaluate_buy_veto(
            signal="强买入",
            action="买入",
            latest_price=20.0,
            structure=structure(),
            trade_point=trade_point("second_buy", "二买"),
            confirmation_missing=False,
            market_context=market("逆风"),
            technical_context=technical("拖累"),
        )

        self.assertTrue(veto.vetoed)
        self.assertEqual(veto.level, "combined")
        self.assertIn("市场逆风叠加技术拖累", "；".join(veto.reasons))

    def test_does_not_veto_non_buy_action(self):
        veto = evaluate_buy_veto(
            signal="观察",
            action="继续持有",
            latest_price=20.0,
            structure=structure(trend="downtrend"),
            trade_point=None,
            confirmation_missing=False,
            technical_context=technical("拖累", "压缩后向下突破"),
        )

        self.assertFalse(veto.vetoed)
        self.assertEqual(veto.level, "none")
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_veto -v
```

Expected: fail because `astockdata.veto` does not exist.

- [ ] **Step 3: Implement `src/astockdata/veto.py`**

Create `VetoContext` and `evaluate_buy_veto()`:

```python
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
    numbers = []
    for part in invalidation.replace("，", " ").split():
        try:
            numbers.append(float(part))
        except ValueError:
            continue
    if not numbers:
        return False
    return latest_price <= numbers[-1] if "跌" in invalidation or "破" in invalidation else latest_price >= numbers[-1]


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
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_veto -v
```

Expected: all `tests.test_veto` tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/astockdata/veto.py tests/test_veto.py
git commit -m "feat: add buy veto rules"
```

### Task 2: Signal Engine Integration

**Files:**
- Modify: `src/astockdata/signals.py`
- Test: `tests/test_signals.py`

- [ ] **Step 1: Write failing signal integration tests**

In `tests/test_signals.py`, import `CentralZone` if needed and add tests:

```python
def third_buy_structure_inside_zone(self):
    bottom1 = Fractal("bottom", "1", 10.0, 1)
    top1 = Fractal("top", "2", 18.0, 5)
    bottom2 = Fractal("bottom", "3", 12.0, 9)
    top2 = Fractal("top", "4", 22.0, 13)
    bottom3 = Fractal("bottom", "5", 19.0, 17)
    zone = CentralZone("1", "3", 12.0, 18.0, 3, "up")
    return ChanStructure(
        merged=[],
        fractals=[bottom1, top1, bottom2, top2, bottom3],
        strokes=[
            Stroke(bottom1, top1, "up", 8.0, 100.0),
            Stroke(top1, bottom2, "down", 6.0, 100.0),
            Stroke(bottom2, top2, "up", 10.0, 100.0),
            Stroke(top2, bottom3, "down", 3.0, 100.0),
        ],
        zones=[zone],
        trend="uptrend",
        up_divergence_risk=False,
        down_divergence_repair=False,
    )

def test_buy_signal_is_rewritten_to_observe_when_vetoed(self):
    engine = ChanSignalEngine()

    signal = engine.evaluate(
        "600519",
        daily_structure=self.third_buy_structure_inside_zone(),
        confirm_structure=self.make_structure("uptrend"),
        latest_price=15.0,
    )

    self.assertEqual(signal.action, "继续持有")
    self.assertEqual(signal.signal, "观察")
    self.assertTrue(signal.veto_context.vetoed)
    self.assertEqual(signal.veto_context.original_action, "买入")
    self.assertIn("买入被否决", "；".join(signal.reasons))
    self.assertLessEqual(signal.confidence, 0.48)

def test_first_buy_is_not_vetoed_by_downtrend_repair(self):
    engine = ChanSignalEngine()

    signal = engine.evaluate(
        "600519",
        daily_structure=self.first_buy_structure(),
        confirm_structure=self.make_structure("uptrend"),
        latest_price=8.8,
    )

    self.assertEqual(signal.action, "买入")
    self.assertFalse(signal.veto_context.vetoed)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_signals -v
```

Expected: fail because `ChanSignal.veto_context` does not exist and `evaluate()` does not rewrite vetoed buys.

- [ ] **Step 3: Wire veto into `signals.py`**

Import:

```python
from .veto import VetoContext, evaluate_buy_veto
```

Add `veto_context: VetoContext | None = None` to `ChanSignal`.

After existing market and technical score adjustments in `evaluate()`, call:

```python
        original_signal = signal
        original_action = map_signal_to_action(signal)
        veto_context = evaluate_buy_veto(
            signal=original_signal,
            action=original_action,
            latest_price=latest_price,
            structure=daily_structure,
            trade_point=trade_point,
            confirmation_missing=confirmation_missing,
            market_context=market_context,
            technical_context=technical_context,
        )
        if veto_context.vetoed and original_action == "买入":
            signal = "观察"
            confidence = min(confidence, 0.48)
            reasons.append(f"买入被否决：{veto_context.summary}")
            risk_notes.append(veto_context.summary)
```

Pass `veto_context=veto_context` into `ChanSignal`.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_signals -v
```

Expected: all signal tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/astockdata/signals.py tests/test_signals.py
git commit -m "feat: apply buy veto to signals"
```

### Task 3: CLI And Web Display

**Files:**
- Modify: `src/astockdata/chan_cli.py`
- Modify: `src/astockdata/web_static.py`
- Test: `tests/test_chan_cli.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Write failing display tests**

In `tests/test_chan_cli.py`, add this import near the other imports:

```python
from astockdata.veto import VetoContext
```

Then update `sample_signal()` by adding this argument to the `ChanSignal(...)` constructor:

```python
veto_context=VetoContext(False, "none", "未触发买入否决条件。", [], "持有", "继续持有"),
```

In `test_render_table_contains_core_fields()` add:

```python
self.assertIn("否决条件", output)
self.assertIn("未触发", output)
```

In `tests/test_web.py`, add assertions:

```python
self.assertIn("否决条件", body)
self.assertIn('id="vetoStatus"', body)
self.assertIn('id="vetoDetail"', body)
self.assertIn("vetoContextText", body)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli tests.test_web -v
```

Expected: fail because CLI/Web do not render veto context.

- [ ] **Step 3: Implement CLI display**

In `chan_cli.py`, add helper:

```python
def _veto_label(signal: ChanSignal) -> str:
    context = signal.veto_context
    if context is None or not context.vetoed:
        return "未触发"
    return "已否决买入"
```

Add `否决条件` to headers and `_veto_label(signal)` to each row after `辅助`.

- [ ] **Step 4: Implement Web display**

In `web_static.py`, add a KV row in the structure section:

```html
<div class="kv"><span>否决条件</span><div class="strength-box"><strong id="vetoStatus">-</strong><span id="vetoDetail" class="inline-hint">运行分析后显示是否有买入否决</span></div></div>
```

Add table header:

```html
<th>否决</th>
```

Add JS helpers:

```javascript
function vetoContextText(context) {
  if (!context || !context.vetoed) return "未触发";
  return "已否决买入";
}

function vetoContextDetail(context) {
  if (!context) return "未触发买入否决条件。";
  return context.summary || "未触发买入否决条件。";
}
```

In `renderPortfolio`, insert `vetoContextText(item.veto_context)` after technical context. In `renderSignal`, set `vetoStatus` and `vetoDetail`.

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli tests.test_web -v
```

Expected: CLI and Web tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/astockdata/chan_cli.py src/astockdata/web_static.py tests/test_chan_cli.py tests/test_web.py
git commit -m "feat: show buy veto context"
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

Expected: command exits with status 0 and JSON contains `veto_context`.

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
