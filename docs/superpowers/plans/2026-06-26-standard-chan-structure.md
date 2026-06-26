# Standard Chan Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conservative standard Chan central-zone layer and use it to make third-buy and third-sell signals easier to validate and understand.

**Architecture:** Extend the existing `chan.py` pipeline after stroke construction by deriving central zones from overlapping stroke ranges. Keep existing trade-point rules intact, but let `chan_points.py` prefer zone-based third-buy and third-sell rules when a recent zone exists. Surface the latest zone through `signals.py` summaries and the existing Web structure panel.

**Tech Stack:** Python dataclasses, unittest, existing static Web UI in `src/astockdata/web_static.py`.

---

### File Map

- Modify `src/astockdata/chan.py`: add `CentralZone`, build zones from strokes, attach zones to `ChanStructure`.
- Modify `src/astockdata/chan_points.py`: check latest zone before simplified third-buy and third-sell fallback rules.
- Modify `src/astockdata/signals.py`: add `CentralZoneSummary` to `StructureSummary` and translate zone state into plain Chinese.
- Modify `src/astockdata/web_static.py`: show latest zone and zone meaning in the structure summary panel.
- Modify `tests/test_chan.py`: cover zone detection and zone direction.
- Modify `tests/test_chan_points.py`: cover zone-based third-buy and third-sell.
- Modify `tests/test_signals.py`: cover structure summary zone fields.

### Task 1: Central Zone Model And Detection

**Files:**
- Modify: `src/astockdata/chan.py`
- Test: `tests/test_chan.py`

- [ ] **Step 1: Write failing central-zone tests**

Add tests inside `ChanStructureTests` that use explicit `Fractal` and `Stroke` instances so the expected zone is unambiguous. Add the helper functions at module level, above `ChanStructureTests`:

```python
from astockdata.chan import CentralZone, Fractal, Stroke, build_central_zones


def fractal(kind, ts, price, index):
    return Fractal(kind, ts, float(price), index)


def stroke(start, end):
    direction = "up" if start.kind == "bottom" and end.kind == "top" else "down"
    return Stroke(start, end, direction, abs(end.price - start.price), 100.0)


def test_build_central_zones_detects_three_stroke_overlap(self):
    top1 = fractal("top", "1", 20, 1)
    bottom1 = fractal("bottom", "2", 10, 5)
    top2 = fractal("top", "3", 18, 9)
    bottom2 = fractal("bottom", "4", 12, 13)
    strokes = [stroke(top1, bottom1), stroke(bottom1, top2), stroke(top2, bottom2)]

    zones = build_central_zones(strokes)

    self.assertEqual(len(zones), 1)
    self.assertEqual(zones[0].start_timestamp, "1")
    self.assertEqual(zones[0].end_timestamp, "4")
    self.assertEqual(zones[0].low, 12.0)
    self.assertEqual(zones[0].high, 18.0)
    self.assertEqual(zones[0].stroke_count, 3)
    self.assertEqual(zones[0].direction, "inside")
```

Add a second test for extension:

```python
def test_build_central_zones_extends_when_next_stroke_overlaps(self):
    top1 = fractal("top", "1", 20, 1)
    bottom1 = fractal("bottom", "2", 10, 5)
    top2 = fractal("top", "3", 18, 9)
    bottom2 = fractal("bottom", "4", 12, 13)
    top3 = fractal("top", "5", 17, 17)
    strokes = [
        stroke(top1, bottom1),
        stroke(bottom1, top2),
        stroke(top2, bottom2),
        stroke(bottom2, top3),
    ]

    zones = build_central_zones(strokes)

    self.assertEqual(len(zones), 1)
    self.assertEqual(zones[0].end_timestamp, "5")
    self.assertEqual(zones[0].stroke_count, 4)
    self.assertEqual(zones[0].low, 12.0)
    self.assertEqual(zones[0].high, 18.0)
```

Add a third test for leave direction:

```python
def test_build_central_zones_marks_up_leave_direction(self):
    top1 = fractal("top", "1", 20, 1)
    bottom1 = fractal("bottom", "2", 10, 5)
    top2 = fractal("top", "3", 18, 9)
    bottom2 = fractal("bottom", "4", 12, 13)
    top3 = fractal("top", "5", 24, 17)
    strokes = [
        stroke(top1, bottom1),
        stroke(bottom1, top2),
        stroke(top2, bottom2),
        stroke(bottom2, top3),
    ]

    zones = build_central_zones(strokes)

    self.assertEqual(zones[0].direction, "up")
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m unittest tests.test_chan -v
```

Expected: fail because `CentralZone` and `build_central_zones` do not exist.

- [ ] **Step 3: Implement central-zone model and detection**

In `src/astockdata/chan.py`, add:

```python
@dataclass(frozen=True)
class CentralZone:
    start_timestamp: str
    end_timestamp: str
    low: float
    high: float
    stroke_count: int
    direction: str
```

Add helpers:

```python
def _stroke_range(stroke: Stroke) -> tuple[float, float]:
    return min(stroke.start.price, stroke.end.price), max(stroke.start.price, stroke.end.price)


def _overlap_range(strokes: list[Stroke]) -> tuple[float, float] | None:
    ranges = [_stroke_range(stroke) for stroke in strokes]
    low = max(item[0] for item in ranges)
    high = min(item[1] for item in ranges)
    if low <= high:
        return low, high
    return None


def _zone_direction(zone_low: float, zone_high: float, stroke: Stroke) -> str:
    low, high = _stroke_range(stroke)
    if low > zone_high:
        return "up"
    if high < zone_low:
        return "down"
    return "inside"
```

Implement:

```python
def build_central_zones(strokes: list[Stroke]) -> list[CentralZone]:
    zones: list[CentralZone] = []
    index = 0
    while index + 2 < len(strokes):
        base = strokes[index : index + 3]
        overlap = _overlap_range(base)
        if overlap is None:
            index += 1
            continue
        low, high = overlap
        end_index = index + 2
        while end_index + 1 < len(strokes):
            next_low, next_high = _stroke_range(strokes[end_index + 1])
            if next_high < low or next_low > high:
                break
            end_index += 1
        last_stroke = strokes[end_index]
        zones.append(
            CentralZone(
                start_timestamp=strokes[index].start.timestamp,
                end_timestamp=last_stroke.end.timestamp,
                low=round(low, 2),
                high=round(high, 2),
                stroke_count=end_index - index + 1,
                direction=_zone_direction(low, high, last_stroke),
            )
        )
        index = end_index + 1
    return zones
```

Add `zones: list[CentralZone]` to `ChanStructure`, and pass `zones=build_central_zones(strokes)` from `analyze_structure`.
Update all direct `ChanStructure(...)` test constructors in `tests/test_chan_points.py` and `tests/test_signals.py` to pass `zones=[]` until those tests intentionally supply zones.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python -m unittest tests.test_chan -v
```

Expected: all `tests.test_chan` tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/astockdata/chan.py tests/test_chan.py
git commit -m "feat: detect Chan central zones"
```

### Task 2: Zone-Based Third Buy And Third Sell

**Files:**
- Modify: `src/astockdata/chan_points.py`
- Test: `tests/test_chan_points.py`

- [ ] **Step 1: Write failing trade-point tests**

Update the `structure` test helper so it passes `zones=[]` by default. Then add:

```python
from astockdata.chan import CentralZone


def test_third_buy_uses_zone_leave_and_pullback_confirmation(self):
    bottom1 = fractal("bottom", "1", 10, 1)
    top1 = fractal("top", "2", 18, 5)
    bottom2 = fractal("bottom", "3", 12, 9)
    top2 = fractal("top", "4", 22, 13)
    bottom3 = fractal("bottom", "5", 19, 17)
    zone = CentralZone("1", "3", 12.0, 18.0, 3, "up")

    point = classify_trade_point(
        structure(
            [
                stroke(bottom1, top1),
                stroke(top1, bottom2),
                stroke(bottom2, top2),
                stroke(top2, bottom3),
            ],
            trend="uptrend",
            zones=[zone],
        ),
        latest_price=20.0,
    )

    self.assertEqual(point.kind, "third_buy")
    self.assertEqual(point.label, "三买")
    self.assertIn("离开最近中枢上方", point.explanation)
    self.assertIn("没有跌回中枢", point.explanation)
```

Add the sell-side mirror:

```python
def test_third_sell_uses_zone_leave_and_rebound_confirmation(self):
    top1 = fractal("top", "1", 22, 1)
    bottom1 = fractal("bottom", "2", 14, 5)
    top2 = fractal("top", "3", 18, 9)
    bottom2 = fractal("bottom", "4", 10, 13)
    top3 = fractal("top", "5", 13, 17)
    zone = CentralZone("1", "3", 14.0, 18.0, 3, "down")

    point = classify_trade_point(
        structure(
            [
                stroke(top1, bottom1),
                stroke(bottom1, top2),
                stroke(top2, bottom2),
                stroke(bottom2, top3),
            ],
            trend="downtrend",
            zones=[zone],
        ),
        latest_price=12.0,
    )

    self.assertEqual(point.kind, "third_sell")
    self.assertEqual(point.label, "三卖")
    self.assertIn("离开最近中枢下方", point.explanation)
    self.assertIn("没有回到中枢", point.explanation)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m unittest tests.test_chan_points -v
```

Expected: fail because `structure(..., zones=[...])` is unsupported and zone-based explanations are not implemented.

- [ ] **Step 3: Implement zone checks before simplified third-buy and third-sell fallback**

In `chan_points.py`, import `CentralZone` from `.chan`, then add helpers:

```python
def _latest_zone(structure: ChanStructure) -> CentralZone | None:
    return structure.zones[-1] if structure.zones else None
```

Then before the existing simplified third-buy/third-sell checks:

```python
    latest_zone = _latest_zone(structure)
    if (
        latest_zone is not None
        and latest_zone.direction == "up"
        and last_stroke.direction == "down"
        and last_bottom is not None
        and last_bottom.price >= latest_zone.high
    ):
        return _point(
            "third_buy",
            "三买",
            "buy",
            last_bottom,
            0.74,
            (
                f"价格已经离开最近中枢上方，中枢区间 {latest_zone.low:.2f}-{latest_zone.high:.2f}，"
                "本次回踩没有跌回中枢，属于三买候选。"
            ),
            f"跌回最近中枢上沿 {latest_zone.high:.2f}",
        )

    if (
        latest_zone is not None
        and latest_zone.direction == "down"
        and last_stroke.direction == "up"
        and last_top is not None
        and last_top.price <= latest_zone.low
    ):
        return _point(
            "third_sell",
            "三卖",
            "sell",
            last_top,
            0.74,
            (
                f"价格已经离开最近中枢下方，中枢区间 {latest_zone.low:.2f}-{latest_zone.high:.2f}，"
                "本次反抽没有回到中枢，属于三卖风险。"
            ),
            f"重新回到最近中枢下沿 {latest_zone.low:.2f}",
        )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python -m unittest tests.test_chan_points -v
```

Expected: all `tests.test_chan_points` tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/astockdata/chan_points.py tests/test_chan_points.py
git commit -m "feat: use central zones for third buy sell"
```

### Task 3: Structure Summary And Web Display

**Files:**
- Modify: `src/astockdata/signals.py`
- Modify: `src/astockdata/web_static.py`
- Test: `tests/test_signals.py`

- [ ] **Step 1: Write failing summary test**

In `tests/test_signals.py`, import `CentralZone` and `summarize_structure`, then add this method inside `SignalTests`:

```python
def test_summarize_structure_includes_latest_central_zone(self):
    zone = CentralZone("2026-06-01", "2026-06-10", 12.0, 18.0, 3, "up")
    summary = summarize_structure(
        ChanStructure(
            merged=[],
            fractals=[],
            strokes=[],
            zones=[zone],
            trend="range",
            up_divergence_risk=False,
            down_divergence_repair=False,
        )
    )

    self.assertEqual(summary.latest_zone.low, 12.0)
    self.assertEqual(summary.latest_zone.high, 18.0)
    self.assertEqual(summary.latest_zone.position_label, "中枢上方")
    self.assertIn("脱离中枢上方", summary.latest_zone.meaning)
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python -m unittest tests.test_signals -v
```

Expected: fail because `latest_zone` summary field does not exist.

- [ ] **Step 3: Add zone summary dataclass and mapper**

In `signals.py`, add:

```python
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
```

Add:

```python
def _zone_position_label(direction: str) -> str:
    labels = {"up": "中枢上方", "down": "中枢下方", "inside": "中枢内部"}
    return labels.get(direction, "中枢内部")


def _zone_meaning(zone: CentralZone) -> str:
    if zone.direction == "up":
        return "价格已经脱离中枢上方，后续重点看回踩是否跌回中枢。"
    if zone.direction == "down":
        return "价格已经脱离中枢下方，后续重点看反抽是否重新回到中枢。"
    return "价格仍在中枢内部震荡，方向还需要等待离开中枢后确认。"


def _central_zone_summary(zone: CentralZone | None) -> CentralZoneSummary | None:
    if zone is None:
        return None
    return CentralZoneSummary(
        start_timestamp=zone.start_timestamp,
        end_timestamp=zone.end_timestamp,
        low=round(zone.low, 2),
        high=round(zone.high, 2),
        stroke_count=zone.stroke_count,
        direction=zone.direction,
        position_label=_zone_position_label(zone.direction),
        meaning=_zone_meaning(zone),
    )
```

Add `latest_zone: CentralZoneSummary | None` to `StructureSummary`, and pass `_central_zone_summary(structure.zones[-1] if structure.zones else None)` in `summarize_structure`.

- [ ] **Step 4: Add Web display rows**

In `web_static.py`, add helper functions:

```javascript
function zoneText(zone) {
  if (!zone) return "-";
  return zone.start_timestamp + " 到 " + zone.end_timestamp + "，" + fmt(zone.low) + "-" + fmt(zone.high);
}

function zonePositionText(zone) {
  if (!zone) return "-";
  return zone.position_label || "-";
}

function zoneMeaningText(zone) {
  if (!zone) return "-";
  return zone.meaning || "-";
}
```

In `renderStructure(signal)`, add rows after `最近一笔`:

```javascript
        ["最近中枢", zoneText(summary.latest_zone)],
        ["中枢位置", zonePositionText(summary.latest_zone)],
        ["结构含义", zoneMeaningText(summary.latest_zone)],
```

- [ ] **Step 5: Run tests to verify GREEN**

Run:

```bash
python -m unittest tests.test_signals -v
```

Expected: all `tests.test_signals` tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/astockdata/signals.py src/astockdata/web_static.py tests/test_signals.py
git commit -m "feat: show central zone summary"
```

### Task 4: Full Verification

**Files:**
- No new files

- [ ] **Step 1: Run all tests**

Run:

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run CLI JSON smoke**

Run:

```bash
python -m astockdata.chan_cli --chan-signal 603337 --json
```

Expected: JSON output includes `daily_summary.latest_zone` when the current stock has enough strokes to form a zone, and the command exits with status 0.

- [ ] **Step 3: Run backtest smoke**

Run:

```bash
python -m astockdata.chan_cli --backtest 603337 --horizons 5 --lookback 80
```

Expected: command exits with status 0 and prints backtest summary sections.

- [ ] **Step 4: Review diff**

Run:

```bash
git diff --stat HEAD~3..HEAD
git status --short --branch
```

Expected: implementation commits are present, only `.DS_Store` remains untracked.
