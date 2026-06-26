# Signal Backtest Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight historical replay backtest that validates buy/sell signals without simulating a full trading account.

**Architecture:** Add a focused `astockdata.backtest` module that consumes already-loaded daily K lines, rolls forward one historical date at a time, generates signals with the existing `ChanSignalEngine`, and summarizes future outcomes. Extend `chan_cli` with `--backtest`, `--horizons`, and `--lookback` while keeping Web UI out of scope for V1.

**Tech Stack:** Python dataclasses, existing `KLine`, `analyze_structure`, `build_technical_context`, `ChanSignalEngine`, standard `unittest`, existing CLI style.

---

## File Structure

- Create `src/astockdata/backtest.py`
  - Owns `BacktestSample`, `BacktestBucketSummary`, `BacktestReport`.
  - Owns `run_signal_backtest`, sample generation, return calculations, grouped summaries.
- Modify `src/astockdata/chan_cli.py`
  - Add parser options: `--backtest`, `--horizons`, `--lookback`.
  - Add `render_backtest_table` and JSON handling for `BacktestReport`.
  - Load daily K lines through `BaiduDailyKLineProvider` for CLI backtests.
- Create `tests/test_backtest.py`
  - Unit-test pure backtest behavior with deterministic fake K lines and stub engines where needed.
- Modify `tests/test_chan_cli.py`
  - Cover parser options and table/JSON rendering for backtest reports.
- Modify `docs/local-analysis.md`
  - Document the backtest CLI command and the interpretation of output.

## Task 1: Backtest Data Model And Bucket Summary

**Files:**
- Create: `src/astockdata/backtest.py`
- Test: `tests/test_backtest.py`

- [ ] **Step 1: Write failing tests for summary math**

Add `tests/test_backtest.py` with:

```python
import unittest

from astockdata.backtest import BacktestSample, summarize_samples


class BacktestTests(unittest.TestCase):
    def test_summarize_samples_calculates_rates_and_averages(self):
        samples = [
            BacktestSample(
                code="600519",
                timestamp="2026-01-01",
                action="买入",
                signal="强买入",
                confidence=0.8,
                strength_label="较强",
                trade_point_label="一买",
                technical_label="助力",
                entry_price=10.0,
                horizon_days=5,
                exit_price=11.0,
                return_pct=10.0,
                favorable=True,
                max_favorable_pct=15.0,
                max_adverse_pct=-2.0,
            ),
            BacktestSample(
                code="600519",
                timestamp="2026-01-02",
                action="买入",
                signal="试买入",
                confidence=0.62,
                strength_label="一般",
                trade_point_label="二买",
                technical_label="拖累",
                entry_price=10.0,
                horizon_days=5,
                exit_price=9.0,
                return_pct=-10.0,
                favorable=False,
                max_favorable_pct=3.0,
                max_adverse_pct=-12.0,
            ),
        ]

        summary = summarize_samples("5日", samples)

        self.assertEqual(summary.name, "5日")
        self.assertEqual(summary.sample_count, 2)
        self.assertEqual(summary.favorable_count, 1)
        self.assertEqual(summary.favorable_rate, 0.5)
        self.assertEqual(summary.average_return_pct, 0.0)
        self.assertEqual(summary.average_max_favorable_pct, 9.0)
        self.assertEqual(summary.average_max_adverse_pct, -7.0)
        self.assertEqual(summary.best_return_pct, 10.0)
        self.assertEqual(summary.worst_return_pct, -10.0)

    def test_summarize_samples_returns_empty_summary(self):
        summary = summarize_samples("empty", [])

        self.assertEqual(summary.sample_count, 0)
        self.assertEqual(summary.favorable_rate, None)
        self.assertEqual(summary.average_return_pct, None)
```

- [ ] **Step 2: Run the tests to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_backtest.BacktestTests.test_summarize_samples_calculates_rates_and_averages tests.test_backtest.BacktestTests.test_summarize_samples_returns_empty_summary -v
```

Expected: import failure because `astockdata.backtest` does not exist.

- [ ] **Step 3: Implement dataclasses and summary math**

Create `src/astockdata/backtest.py` with:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BacktestSample:
    code: str
    timestamp: str
    action: str
    signal: str
    confidence: float
    strength_label: str
    trade_point_label: str
    technical_label: str
    entry_price: float
    horizon_days: int
    exit_price: float
    return_pct: float
    favorable: bool
    max_favorable_pct: float
    max_adverse_pct: float


@dataclass(frozen=True)
class BacktestBucketSummary:
    name: str
    sample_count: int
    favorable_count: int
    favorable_rate: float | None
    average_return_pct: float | None
    average_max_favorable_pct: float | None
    average_max_adverse_pct: float | None
    best_return_pct: float | None
    worst_return_pct: float | None


@dataclass(frozen=True)
class BacktestReport:
    code: str
    start_timestamp: str | None
    end_timestamp: str | None
    horizons: list[int]
    sample_count: int
    skipped_hold_count: int
    by_horizon: list[BacktestBucketSummary]
    by_action: list[BacktestBucketSummary]
    by_trade_point: list[BacktestBucketSummary]
    by_strength: list[BacktestBucketSummary]
    by_technical: list[BacktestBucketSummary]
    samples: list[BacktestSample]
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def summarize_samples(name: str, samples: list[BacktestSample]) -> BacktestBucketSummary:
    if not samples:
        return BacktestBucketSummary(name, 0, 0, None, None, None, None, None, None)
    favorable_count = sum(1 for sample in samples if sample.favorable)
    return BacktestBucketSummary(
        name=name,
        sample_count=len(samples),
        favorable_count=favorable_count,
        favorable_rate=round(favorable_count / len(samples), 2),
        average_return_pct=_average([sample.return_pct for sample in samples]),
        average_max_favorable_pct=_average([sample.max_favorable_pct for sample in samples]),
        average_max_adverse_pct=_average([sample.max_adverse_pct for sample in samples]),
        best_return_pct=round(max(sample.return_pct for sample in samples), 2),
        worst_return_pct=round(min(sample.return_pct for sample in samples), 2),
    )
```

- [ ] **Step 4: Run tests to verify GREEN**

Run the same command from Step 2.

Expected: both tests pass.

## Task 2: Outcome Sample Generation

**Files:**
- Modify: `src/astockdata/backtest.py`
- Test: `tests/test_backtest.py`

- [ ] **Step 1: Add failing tests for buy and sell outcomes**

Append tests:

```python
from astockdata.backtest import build_outcome_sample
from astockdata.kline import KLine
from astockdata.signals import ChanSignal


def kline(timestamp, close, high=None, low=None):
    return KLine("600519", "1d", timestamp, close, high or close, low or close, close, 100.0, 1000.0)


def signal(action, trade_point_label="一买", technical_label="助力"):
    return ChanSignal(
        code="600519",
        action=action,
        signal="强买入" if action == "买入" else "减仓",
        confidence=0.78,
        strength_label="较强",
        confirmed=True,
        intraday=False,
        confirmation_missing=True,
        reasons=[],
        invalidations=[],
        risk_notes=[],
        trade_point=None,
        technical_context=None,
    )


class BacktestTests(unittest.TestCase):
    ...

    def test_buy_outcome_uses_forward_return_and_drawdown(self):
        entry = kline("2026-01-01", 10.0)
        future = [
            kline("2026-01-02", 10.5, high=11.0, low=9.8),
            kline("2026-01-03", 11.0, high=11.5, low=10.2),
        ]

        sample = build_outcome_sample("600519", signal("买入"), entry, future, 2)

        self.assertTrue(sample.favorable)
        self.assertEqual(sample.return_pct, 10.0)
        self.assertEqual(sample.max_favorable_pct, 15.0)
        self.assertEqual(sample.max_adverse_pct, -2.0)

    def test_sell_outcome_uses_inverse_return_and_adverse_rally(self):
        entry = kline("2026-01-01", 10.0)
        future = [
            kline("2026-01-02", 9.5, high=10.4, low=9.0),
            kline("2026-01-03", 9.0, high=9.8, low=8.8),
        ]

        sample = build_outcome_sample("600519", signal("卖出"), entry, future, 2)

        self.assertTrue(sample.favorable)
        self.assertEqual(sample.return_pct, 10.0)
        self.assertEqual(sample.max_favorable_pct, 12.0)
        self.assertEqual(sample.max_adverse_pct, -4.0)
```

Adjust the helper `signal()` after implementation to attach trade point and technical labels if needed.

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_backtest -v
```

Expected: failure because `build_outcome_sample` does not exist.

- [ ] **Step 3: Implement `build_outcome_sample`**

Add to `src/astockdata/backtest.py`:

```python
from .kline import KLine
from .signals import ChanSignal


def _pct(current: float, base: float) -> float:
    if base <= 0:
        return 0.0
    return (current - base) / base * 100


def _trade_point_label(signal: ChanSignal) -> str:
    if signal.trade_point is None:
        return "无明确买卖点"
    return signal.trade_point.label


def _technical_label(signal: ChanSignal) -> str:
    if signal.technical_context is None:
        return "-"
    return signal.technical_context.label


def build_outcome_sample(
    code: str,
    signal: ChanSignal,
    entry: KLine,
    future_rows: list[KLine],
    horizon_days: int,
) -> BacktestSample:
    exit_row = future_rows[horizon_days - 1]
    if signal.action == "卖出":
        return_pct = _pct(entry.close, exit_row.close)
        max_favorable = _pct(entry.close, min(row.low for row in future_rows))
        max_adverse = -_pct(max(row.high for row in future_rows), entry.close)
    else:
        return_pct = _pct(exit_row.close, entry.close)
        max_favorable = _pct(max(row.high for row in future_rows), entry.close)
        max_adverse = _pct(min(row.low for row in future_rows), entry.close)
    return BacktestSample(
        code=code,
        timestamp=entry.timestamp,
        action=signal.action,
        signal=signal.signal,
        confidence=signal.confidence,
        strength_label=signal.strength_label,
        trade_point_label=_trade_point_label(signal),
        technical_label=_technical_label(signal),
        entry_price=round(entry.close, 2),
        horizon_days=horizon_days,
        exit_price=round(exit_row.close, 2),
        return_pct=round(return_pct, 2),
        favorable=return_pct > 0,
        max_favorable_pct=round(max_favorable, 2),
        max_adverse_pct=round(max_adverse, 2),
    )
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_backtest -v
```

Expected: all current backtest tests pass.

## Task 3: Rolling Signal Backtest

**Files:**
- Modify: `src/astockdata/backtest.py`
- Test: `tests/test_backtest.py`

- [ ] **Step 1: Add failing tests for rolling backtest**

Append tests:

```python
from astockdata.backtest import run_signal_backtest


class FakeEngine:
    def __init__(self):
        self.seen_latest_timestamps = []

    def evaluate(self, **kwargs):
        rows = kwargs["recent_klines"]
        self.seen_latest_timestamps.append(rows[-1].timestamp)
        action = "买入" if rows[-1].close >= rows[-2].close else "卖出"
        signal_name = "强买入" if action == "买入" else "减仓"
        return ChanSignal(
            code=kwargs["code"],
            action=action,
            signal=signal_name,
            confidence=0.78,
            strength_label="较强",
            confirmed=True,
            intraday=False,
            confirmation_missing=True,
            reasons=[],
            invalidations=[],
            risk_notes=[],
            trade_point=None,
            technical_context=kwargs["technical_context"],
        )


class BacktestTests(unittest.TestCase):
    ...

    def test_run_signal_backtest_rolls_without_future_leakage(self):
        rows = [kline(f"2026-01-{index + 1:02d}", 10 + index * 0.1) for index in range(12)]
        engine = FakeEngine()

        report = run_signal_backtest("600519", rows, horizons=[2], min_history=5, engine=engine)

        self.assertEqual(report.code, "600519")
        self.assertGreater(report.sample_count, 0)
        self.assertNotIn("2026-01-12", engine.seen_latest_timestamps)
        self.assertEqual(report.by_horizon[0].name, "2日")
        self.assertEqual(report.by_action[0].name, "买入")

    def test_run_signal_backtest_returns_empty_report_when_rows_are_insufficient(self):
        report = run_signal_backtest("600519", [kline("2026-01-01", 10.0)], horizons=[5], min_history=5)

        self.assertEqual(report.sample_count, 0)
        self.assertIn("样本不足", report.summary)
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_backtest -v
```

Expected: failure because `run_signal_backtest` does not exist.

- [ ] **Step 3: Implement rolling backtest and grouping**

Add functions:

```python
from collections import defaultdict

from .chan import analyze_structure
from .signals import ChanSignalEngine
from .technical_context import build_technical_context


def _group(samples: list[BacktestSample], key) -> list[BacktestBucketSummary]:
    buckets: dict[str, list[BacktestSample]] = defaultdict(list)
    for sample in samples:
        buckets[str(key(sample))].append(sample)
    return [summarize_samples(name, buckets[name]) for name in sorted(buckets)]


def run_signal_backtest(
    code: str,
    rows: list[KLine],
    horizons: list[int] | None = None,
    min_history: int = 60,
    engine: ChanSignalEngine | None = None,
) -> BacktestReport:
    horizons = horizons or [5, 10, 20]
    max_horizon = max(horizons) if horizons else 0
    if len(rows) < min_history + max_horizon:
        return BacktestReport(
            code=code,
            start_timestamp=rows[0].timestamp if rows else None,
            end_timestamp=rows[-1].timestamp if rows else None,
            horizons=horizons,
            sample_count=0,
            skipped_hold_count=0,
            by_horizon=[],
            by_action=[],
            by_trade_point=[],
            by_strength=[],
            by_technical=[],
            samples=[],
            summary="样本不足，无法形成可靠回测统计。",
        )
    engine = engine or ChanSignalEngine()
    samples: list[BacktestSample] = []
    skipped_hold_count = 0
    last_entry_index = len(rows) - max_horizon - 1
    for index in range(min_history - 1, last_entry_index + 1):
        history = rows[: index + 1]
        signal = engine.evaluate(
            code=code,
            daily_structure=analyze_structure(history),
            confirm_structure=None,
            latest_price=history[-1].close,
            recent_klines=history,
            technical_context=build_technical_context(history),
        )
        if signal.action not in {"买入", "卖出"}:
            skipped_hold_count += 1
            continue
        for horizon in horizons:
            future_rows = rows[index + 1 : index + 1 + horizon]
            if len(future_rows) < horizon:
                continue
            samples.append(build_outcome_sample(code, signal, rows[index], future_rows, horizon))
    return BacktestReport(
        code=code,
        start_timestamp=rows[0].timestamp,
        end_timestamp=rows[-1].timestamp,
        horizons=horizons,
        sample_count=len(samples),
        skipped_hold_count=skipped_hold_count,
        by_horizon=_group(samples, lambda sample: f"{sample.horizon_days}日"),
        by_action=_group(samples, lambda sample: sample.action),
        by_trade_point=_group(samples, lambda sample: sample.trade_point_label),
        by_strength=_group(samples, lambda sample: sample.strength_label),
        by_technical=_group(samples, lambda sample: sample.technical_label),
        samples=samples,
        summary=f"共生成{len(samples)}条买卖信号回测样本，跳过{skipped_hold_count}条继续持有信号。",
    )
```

- [ ] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_backtest -v
```

Expected: all backtest tests pass.

## Task 4: CLI Backtest Rendering And Arguments

**Files:**
- Modify: `src/astockdata/chan_cli.py`
- Test: `tests/test_chan_cli.py`

- [ ] **Step 1: Add failing CLI tests**

Append tests:

```python
from astockdata.backtest import BacktestBucketSummary, BacktestReport, BacktestSample
from astockdata.chan_cli import parse_horizons, render_backtest_json, render_backtest_table


class ChanCliTests(unittest.TestCase):
    ...

    def sample_backtest_report(self):
        sample = BacktestSample(
            code="600519",
            timestamp="2026-01-01",
            action="买入",
            signal="强买入",
            confidence=0.78,
            strength_label="较强",
            trade_point_label="一买",
            technical_label="助力",
            entry_price=10.0,
            horizon_days=5,
            exit_price=11.0,
            return_pct=10.0,
            favorable=True,
            max_favorable_pct=15.0,
            max_adverse_pct=-2.0,
        )
        summary = BacktestBucketSummary("5日", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)
        return BacktestReport(
            code="600519",
            start_timestamp="2026-01-01",
            end_timestamp="2026-02-01",
            horizons=[5],
            sample_count=1,
            skipped_hold_count=0,
            by_horizon=[summary],
            by_action=[BacktestBucketSummary("买入", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            by_trade_point=[BacktestBucketSummary("一买", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            by_strength=[BacktestBucketSummary("较强", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            by_technical=[BacktestBucketSummary("助力", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            samples=[sample],
            summary="共生成1条买卖信号回测样本，跳过0条继续持有信号。",
        )

    def test_parse_horizons(self):
        self.assertEqual(parse_horizons("5,10,20"), [5, 10, 20])

    def test_render_backtest_table_contains_core_fields(self):
        buf = StringIO()

        render_backtest_table(self.sample_backtest_report(), buf)

        output = buf.getvalue()
        self.assertIn("回测摘要", output)
        self.assertIn("有利率", output)
        self.assertIn("平均收益", output)
        self.assertIn("5日", output)

    def test_render_backtest_json_is_machine_readable(self):
        buf = StringIO()

        render_backtest_json(self.sample_backtest_report(), buf)

        data = json.loads(buf.getvalue())
        self.assertEqual(data["code"], "600519")
        self.assertEqual(data["sample_count"], 1)
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli -v
```

Expected: failures because `parse_horizons`, `render_backtest_table`, and `render_backtest_json` do not exist.

- [ ] **Step 3: Implement CLI helpers and parser args**

Modify imports in `chan_cli.py`:

```python
from .backtest import BacktestBucketSummary, BacktestReport, run_signal_backtest
from .kline import BaiduDailyKLineProvider
```

Add helpers:

```python
def parse_horizons(raw: str) -> list[int]:
    values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not values or any(value <= 0 for value in values):
        raise ValueError("horizons must be positive integers")
    return values


def _fmt_pct(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}%"


def _render_bucket_section(title: str, rows: list[BacktestBucketSummary], out: TextIO) -> None:
    print(title, file=out)
    print("\t".join(["分组", "样本数", "有利次数", "有利率", "平均收益", "平均最大有利", "平均最大不利"]), file=out)
    for row in rows:
        print(
            "\t".join(
                [
                    row.name,
                    str(row.sample_count),
                    str(row.favorable_count),
                    _fmt_pct(row.favorable_rate * 100 if row.favorable_rate is not None else None),
                    _fmt_pct(row.average_return_pct),
                    _fmt_pct(row.average_max_favorable_pct),
                    _fmt_pct(row.average_max_adverse_pct),
                ]
            ),
            file=out,
        )


def render_backtest_table(report: BacktestReport, out: TextIO = sys.stdout) -> None:
    print(f"回测摘要：{report.summary}", file=out)
    print(f"代码：{report.code}  区间：{report.start_timestamp or '-'} -> {report.end_timestamp or '-'}", file=out)
    _render_bucket_section("按周期", report.by_horizon, out)
    _render_bucket_section("按动作", report.by_action, out)
    _render_bucket_section("按买卖点", report.by_trade_point, out)
    _render_bucket_section("按信号力度", report.by_strength, out)
    _render_bucket_section("按辅助确认", report.by_technical, out)


def render_backtest_json(report: BacktestReport, out: TextIO = sys.stdout) -> None:
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), file=out)
```

Add parser args:

```python
parser.add_argument("--backtest", help="Run historical signal validation for one code or stock name.")
parser.add_argument("--horizons", default="5,10,20", help="Comma-separated forward horizons for --backtest.")
parser.add_argument("--lookback", type=int, default=260, help="Limit daily K-lines used by --backtest.")
```

- [ ] **Step 4: Verify helper tests GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_chan_cli -v
```

Expected: CLI helper tests pass.

## Task 5: CLI Backtest Execution Path

**Files:**
- Modify: `src/astockdata/chan_cli.py`
- Test: `tests/test_chan_cli.py`
- Docs: `docs/local-analysis.md`

- [ ] **Step 1: Add command execution test with fakes if needed**

If the existing `main()` is hard to test without network, keep the unit tests on parser/render helpers and implement the execution path manually. Verify with a local CLI smoke command after implementation.

- [ ] **Step 2: Implement `--backtest` branch in `main`**

Add near the start of `main()` after parsing:

```python
if args.backtest:
    code = args.backtest
    horizons = parse_horizons(args.horizons)
    provider = BaiduDailyKLineProvider()
    rows = provider.daily_klines(code)
    if args.lookback and args.lookback > 0:
        rows = rows[-args.lookback :]
    report = run_signal_backtest(code, rows, horizons=horizons)
    if args.json:
        render_backtest_json(report)
    else:
        render_backtest_table(report)
    return 0
```

Keep this branch separate from portfolio/single-signal analysis.

- [ ] **Step 3: Document CLI usage**

Add to `docs/local-analysis.md` under 缠论交易信号:

```markdown
历史信号验证：

```bash
PYTHONPATH=src python -m astockdata.chan_cli --backtest 600519 --horizons 5,10,20 --lookback 260
```

回测会逐日回放历史 K 线，只用当日及以前的数据生成信号，再统计未来 5/10/20 个交易日是否有利。第一版不模拟资金曲线，也不纳入历史市场环境。
```

- [ ] **Step 4: Run full tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass.

## Task 6: Manual Smoke And Commit

**Files:**
- No code changes unless smoke exposes a bug.

- [ ] **Step 1: Run CLI smoke with JSON on a known code**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m astockdata.chan_cli --backtest 600519 --horizons 5 --lookback 120 --json
```

Expected: JSON object with `code`, `sample_count`, `by_horizon`, and `samples`. If network/data source fails, record the failure and rely on unit tests for pure logic.

- [ ] **Step 2: Run final full test suite**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit implementation**

Run:

```bash
git add src/astockdata/backtest.py src/astockdata/chan_cli.py tests/test_backtest.py tests/test_chan_cli.py docs/local-analysis.md
git commit -m "feat: add signal backtest validation"
```

Expected: one implementation commit. Do not stage `.DS_Store`.

- [ ] **Step 4: Push when credentials are available**

Run:

```bash
git push chanlun feat/chan-buy-sell-points
```

Expected: branch updates on `JeffreyCaicai/chanlunStockAnalysis`. If GitHub credentials are unavailable, leave the local commit ahead and report the exact error.

## Self-Review

- Spec coverage: the plan implements a pure backtest module, rolling no-future signal generation, multi-horizon samples, grouped summaries, CLI table/JSON output, docs, and tests. Web UI and historical market environment are intentionally excluded per spec.
- Placeholder scan: no placeholder tasks remain; each implementation step names files, code shape, commands, and expected outcomes.
- Type consistency: `BacktestSample`, `BacktestBucketSummary`, `BacktestReport`, `run_signal_backtest`, `render_backtest_table`, and `render_backtest_json` are named consistently across tasks.
