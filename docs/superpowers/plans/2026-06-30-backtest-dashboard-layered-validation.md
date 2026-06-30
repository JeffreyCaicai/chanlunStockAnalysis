# Signal Backtest Dashboard And Layered Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single-stock Web backtest dashboard that shows whether historical buy/sell signals worked over 5, 10, and 20 trading days, with layered validation by action, buy/sell point, signal strength, and technical context.

**Architecture:** Reuse `src/astockdata/backtest.py` as the domain/report layer. Add `/api/backtest` in `src/astockdata/web.py` to resolve the stock, fetch daily K-lines through the existing analyzer provider, and return `BacktestReport.to_dict()`. Extend `src/astockdata/web_static.py` with a compact table-oriented dashboard and client-side rendering helpers.

**Tech Stack:** Python standard library HTTP server, existing dataclasses, existing K-line providers, existing `unittest` suite, plain HTML/CSS/JavaScript.

---

## File Structure

- Modify `src/astockdata/web.py`
  - Add request parsing helpers for backtest horizons and minimum history.
  - Add API orchestration for `POST /api/backtest`.
  - Import and call `run_signal_backtest`.
- Modify `src/astockdata/web_static.py`
  - Add the "运行复盘" input action.
  - Add the "信号复盘" dashboard markup.
  - Add JavaScript helpers that render overview metrics, grouped summaries, recent samples, and JSON.
- Modify `tests/test_web.py`
  - Add fake resolver, fake daily K-line provider, and fake backtest engine to test `/api/backtest` without live network.
  - Add endpoint tests and static HTML assertions.
- Do not modify `src/astockdata/backtest.py` unless implementation reveals a missing grouping field that is required by the accepted spec. The current report already includes `by_horizon`, `by_action`, `by_trade_point`, `by_strength`, `by_technical`, and `samples`.

## Task 1: Add `/api/backtest`

**Files:**
- Modify: `tests/test_web.py`
- Modify: `src/astockdata/web.py`

- [ ] **Step 1: Write the failing endpoint tests**

Add these imports near the top of `tests/test_web.py`:

```python
from astockdata.kline import KLine
from astockdata.resolver import StockIdentity
```

Replace the current `FakeAnalyzer` with this expanded version:

```python
class FakeResolver:
    def resolve(self, query):
        if query == "意华股份":
            return StockIdentity(code="002897", name="意华股份", query=query)
        return StockIdentity(code=query, name="贵州茅台", query=query)


class FakeDailyKLineProvider:
    def daily_klines(self, code):
        return [
            KLine(code, "1d", f"2026-01-{index + 1:02d}", 10 + index, 10 + index + 0.8, 10 + index - 0.6, 10 + index, 100.0, 1000.0)
            for index in range(14)
        ]

    def intraday_klines(self, code, period="30m"):
        return []


class FakeBacktestEngine:
    def evaluate(self, **kwargs):
        rows = kwargs["recent_klines"]
        action = "买入" if len(rows) % 2 == 0 else "卖出"
        return ChanSignal(
            code=kwargs["code"],
            action=action,
            signal="强买入" if action == "买入" else "减仓",
            confidence=0.72,
            strength_label="较强",
            confirmed=True,
            intraday=False,
            confirmation_missing=False,
            reasons=[],
            invalidations=[],
            risk_notes=[],
            trade_point=None,
            technical_context=kwargs.get("technical_context"),
        )


class FakeAnalyzer:
    def __init__(self):
        self.resolver = FakeResolver()
        self.kline_provider = FakeDailyKLineProvider()
        self.engine = FakeBacktestEngine()

    def analyze(self, code, position=None, intraday=False):
        resolved_code = "002897" if code == "意华股份" else code
        stock_name = "意华股份" if code == "意华股份" else "贵州茅台"
        return ChanSignal(
            code=resolved_code,
            stock_name=stock_name,
            action="买入",
            signal="试买入",
            confidence=0.62,
            confirmed=not intraday,
            intraday=intraday,
            confirmation_missing=True,
            reasons=["30分钟确认数据不可用，信号降级"],
            invalidations=["跌破 10.00"],
            risk_notes=["试买入不适合重仓"],
            position_context=position,
        )
```

Add these tests inside `WebTests`:

```python
    def test_backtest_endpoint_returns_report_for_stock_name(self):
        payload = json.dumps({"code": "意华股份", "horizons": [2], "min_history": 5}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["code"], "002897")
        self.assertEqual(data["stock_name"], "意华股份")
        self.assertEqual(data["report"]["code"], "002897")
        self.assertEqual(data["report"]["horizons"], [2])
        self.assertGreater(data["report"]["sample_count"], 0)
        self.assertIn("by_horizon", data["report"])
        self.assertIn("samples", data["report"])

    def test_backtest_endpoint_requires_code(self):
        payload = json.dumps({"horizons": [5]}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("code is required", json.loads(body)["error"])

    def test_backtest_endpoint_rejects_invalid_horizons(self):
        payload = json.dumps({"code": "600519", "horizons": [0]}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("horizons must be positive integers", json.loads(body)["error"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: FAIL because `/api/backtest` returns `404 not found`.

- [ ] **Step 3: Implement the endpoint**

In `src/astockdata/web.py`, add this import:

```python
from .backtest import run_signal_backtest
```

Add these helpers below `_position_from_payload`:

```python
def _horizons_from_payload(payload: dict[str, Any]) -> list[int]:
    raw_horizons = payload.get("horizons") or [5, 10, 20]
    if not isinstance(raw_horizons, list):
        raise ValueError("horizons must be a list of positive integers")
    horizons = [int(item) for item in raw_horizons]
    if not horizons or any(item <= 0 for item in horizons):
        raise ValueError("horizons must be positive integers")
    return horizons


def _min_history_from_payload(payload: dict[str, Any]) -> int:
    value = int(payload.get("min_history") or 60)
    if value <= 0:
        raise ValueError("min_history must be positive")
    return value


def _run_backtest(analyzer: ChanAnalyzer, query: str, payload: dict[str, Any]) -> dict[str, Any]:
    identity = analyzer.resolver.resolve(query)
    daily_rows = analyzer.kline_provider.daily_klines(identity.code)
    if not daily_rows:
        raise RuntimeError(f"No daily K-line data returned for {identity.code}")
    report = run_signal_backtest(
        identity.code,
        daily_rows,
        horizons=_horizons_from_payload(payload),
        min_history=_min_history_from_payload(payload),
        engine=analyzer.engine,
    )
    return {
        "code": identity.code,
        "stock_name": identity.name,
        "report": report.to_dict(),
    }
```

Add this route inside `handle_api_request`, after `/api/analyze` and before `/api/analyze-portfolio`:

```python
    if method == "POST" and route == "/api/backtest":
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
            code = str(payload.get("code") or "").strip()
            if not code:
                return _json_response(400, {"error": "code is required"})
            return _json_response(200, _run_backtest(analyzer, code, payload))
        except Exception as exc:
            return _json_response(400, {"error": str(exc)})
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web tests.test_backtest -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/astockdata/web.py tests/test_web.py
git commit -m "feat: add web backtest endpoint"
```

## Task 2: Add Backtest Dashboard Markup

**Files:**
- Modify: `tests/test_web.py`
- Modify: `src/astockdata/web_static.py`

- [ ] **Step 1: Write the failing static HTML assertions**

In `tests/test_web.py`, extend `test_root_serves_html` with:

```python
        self.assertIn("运行复盘", body)
        self.assertIn('id="backtestButton"', body)
        self.assertIn("信号复盘", body)
        self.assertIn("复盘总览", body)
        self.assertIn('id="backtestOverview"', body)
        self.assertIn("周期表现", body)
        self.assertIn('id="backtestHorizonRows"', body)
        self.assertIn("分层验证", body)
        self.assertIn('id="backtestActionRows"', body)
        self.assertIn('id="backtestTradePointRows"', body)
        self.assertIn('id="backtestStrengthRows"', body)
        self.assertIn('id="backtestTechnicalRows"', body)
        self.assertIn("最近信号样本", body)
        self.assertIn('id="backtestSampleRows"', body)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: FAIL because the new backtest markup is not present.

- [ ] **Step 3: Add CSS for compact backtest tables**

In `src/astockdata/web_static.py`, add these CSS rules near the existing table and portfolio styles:

```css
    .backtest-overview {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 8px 0 12px;
      font-size: 13px;
    }
    .backtest-overview div {
      border-bottom: 1px solid var(--line);
      padding: 6px 0;
      min-width: 0;
    }
    .backtest-overview span {
      display: block;
      color: var(--muted);
      margin-bottom: 2px;
    }
    .backtest-overview strong {
      display: block;
      overflow-wrap: anywhere;
    }
    .backtest-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .backtest-table-title {
      margin: 10px 0 4px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }
```

Inside the existing `@media (max-width: 760px)` block, add:

```css
      .backtest-overview { grid-template-columns: 1fr; }
      .backtest-grid { grid-template-columns: 1fr; }
```

- [ ] **Step 4: Add the input button**

In the input panel, immediately after the existing "运行分析" button, add:

```html
      <button id="backtestButton" class="secondary" onclick="runBacktest()">运行复盘</button>
      <p id="backtestState" class="hint">用历史日K线复盘过去买卖信号，观察5日、10日、20日后的表现。</p>
```

- [ ] **Step 5: Add the dashboard markup**

In the analysis panel, place this block after the "最近K线走势" chart box and before "背驰说明":

```html
      <h2 style="margin-top:18px">信号复盘</h2>
      <div id="backtestOverview" class="backtest-overview">
        <div><span>股票</span><strong>-</strong></div>
        <div><span>复盘区间</span><strong>-</strong></div>
        <div><span>买卖样本</span><strong>-</strong></div>
        <div><span>跳过观察</span><strong>-</strong></div>
      </div>
      <div id="backtestSummary" class="hint">点击“运行复盘”后显示历史信号验证结果。</div>
      <h2 style="margin-top:18px">周期表现</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>周期</th>
              <th>样本</th>
              <th>胜率</th>
              <th>平均收益</th>
              <th>最大顺向</th>
              <th>最大逆向</th>
              <th>最好</th>
              <th>最差</th>
            </tr>
          </thead>
          <tbody id="backtestHorizonRows"></tbody>
        </table>
      </div>
      <h2 style="margin-top:18px">分层验证</h2>
      <div class="backtest-grid">
        <div>
          <div class="backtest-table-title">按动作</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>分层</th><th>样本</th><th>胜率</th><th>平均收益</th><th>最大逆向</th></tr></thead>
              <tbody id="backtestActionRows"></tbody>
            </table>
          </div>
        </div>
        <div>
          <div class="backtest-table-title">按买卖点</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>分层</th><th>样本</th><th>胜率</th><th>平均收益</th><th>最大逆向</th></tr></thead>
              <tbody id="backtestTradePointRows"></tbody>
            </table>
          </div>
        </div>
        <div>
          <div class="backtest-table-title">按力度</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>分层</th><th>样本</th><th>胜率</th><th>平均收益</th><th>最大逆向</th></tr></thead>
              <tbody id="backtestStrengthRows"></tbody>
            </table>
          </div>
        </div>
        <div>
          <div class="backtest-table-title">按辅助确认</div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>分层</th><th>样本</th><th>胜率</th><th>平均收益</th><th>最大逆向</th></tr></thead>
              <tbody id="backtestTechnicalRows"></tbody>
            </table>
          </div>
        </div>
      </div>
      <h2 style="margin-top:18px">最近信号样本</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>日期</th>
              <th>动作</th>
              <th>内部信号</th>
              <th>买卖点</th>
              <th>力度</th>
              <th>辅助</th>
              <th>周期</th>
              <th>入场</th>
              <th>退出</th>
              <th>收益</th>
              <th>结果</th>
            </tr>
          </thead>
          <tbody id="backtestSampleRows"></tbody>
        </table>
      </div>
```

- [ ] **Step 6: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/astockdata/web_static.py tests/test_web.py
git commit -m "feat: add backtest dashboard shell"
```

## Task 3: Render Backtest Results In The Web UI

**Files:**
- Modify: `tests/test_web.py`
- Modify: `src/astockdata/web_static.py`

- [ ] **Step 1: Write failing static JavaScript assertions**

In `tests/test_web.py`, extend `test_root_serves_html` with:

```python
        self.assertIn("runBacktest", body)
        self.assertIn("renderBacktest", body)
        self.assertIn("renderBacktestSummaryTable", body)
        self.assertIn("renderBacktestSamples", body)
        self.assertIn("backtestPercent", body)
        self.assertIn("/api/backtest", body)
        self.assertIn("复盘中，请稍候", body)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: FAIL because the rendering functions do not exist.

- [ ] **Step 3: Add formatting and table helpers**

In `src/astockdata/web_static.py`, add these JavaScript helpers after `fmt(value)`:

```javascript
    function backtestPercent(value) {
      if (value === null || value === undefined || value === "") return "-";
      return (Number(value) * 100).toFixed(0) + "%";
    }
    function signedPct(value) {
      if (value === null || value === undefined || value === "") return "-";
      const number = Number(value);
      const prefix = number > 0 ? "+" : "";
      return prefix + number.toFixed(2) + "%";
    }
    function clearRows(id) {
      document.getElementById(id).innerHTML = "";
    }
    function appendCell(row, value) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    }
    function renderEmptyRow(id, colSpan, text) {
      const body = document.getElementById(id);
      body.innerHTML = "";
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = colSpan;
      cell.textContent = text;
      row.appendChild(cell);
      body.appendChild(row);
    }
```

- [ ] **Step 4: Add summary table rendering**

In `src/astockdata/web_static.py`, add this function after `renderPortfolio(results)`:

```javascript
    function renderBacktestSummaryTable(id, rows, compact) {
      const body = document.getElementById(id);
      body.innerHTML = "";
      if (!rows || !rows.length) {
        renderEmptyRow(id, compact ? 5 : 8, "暂无复盘样本");
        return;
      }
      rows.forEach((item) => {
        const row = document.createElement("tr");
        appendCell(row, item.name || "-");
        appendCell(row, fmt(item.sample_count));
        appendCell(row, backtestPercent(item.favorable_rate));
        appendCell(row, signedPct(item.average_return_pct));
        if (compact) {
          appendCell(row, signedPct(item.average_max_adverse_pct));
        } else {
          appendCell(row, signedPct(item.average_max_favorable_pct));
          appendCell(row, signedPct(item.average_max_adverse_pct));
          appendCell(row, signedPct(item.best_return_pct));
          appendCell(row, signedPct(item.worst_return_pct));
        }
        body.appendChild(row);
      });
    }
```

- [ ] **Step 5: Add sample list rendering**

In `src/astockdata/web_static.py`, add this function after `renderBacktestSummaryTable`:

```javascript
    function renderBacktestSamples(samples) {
      const body = document.getElementById("backtestSampleRows");
      body.innerHTML = "";
      const recent = (samples || []).slice(-20).reverse();
      if (!recent.length) {
        renderEmptyRow("backtestSampleRows", 11, "暂无买卖信号样本");
        return;
      }
      recent.forEach((sample) => {
        const row = document.createElement("tr");
        appendCell(row, sample.timestamp || "-");
        appendCell(row, sample.action || "-");
        appendCell(row, sample.signal || "-");
        appendCell(row, sample.trade_point_label || "-");
        appendCell(row, sample.strength_label || "-");
        appendCell(row, sample.technical_label || "-");
        appendCell(row, sample.horizon_days ? sample.horizon_days + "日" : "-");
        appendCell(row, fmt(sample.entry_price));
        appendCell(row, fmt(sample.exit_price));
        appendCell(row, signedPct(sample.return_pct));
        appendCell(row, sample.favorable ? "有利" : "不利");
        body.appendChild(row);
      });
    }
```

- [ ] **Step 6: Add top-level backtest rendering**

In `src/astockdata/web_static.py`, add this function after `renderBacktestSamples`:

```javascript
    function renderBacktest(payload) {
      const report = (payload && payload.report) || {};
      const overview = document.getElementById("backtestOverview");
      const stockName = payload && payload.stock_name ? payload.stock_name + "（" + payload.code + "）" : ((payload && payload.code) || "-");
      overview.innerHTML = "";
      [
        ["股票", stockName],
        ["复盘区间", (report.start_timestamp || "-") + " 到 " + (report.end_timestamp || "-")],
        ["买卖样本", fmt(report.sample_count)],
        ["跳过观察", fmt(report.skipped_hold_count)]
      ].forEach(([label, value]) => {
        const item = document.createElement("div");
        const labelNode = document.createElement("span");
        const valueNode = document.createElement("strong");
        labelNode.textContent = label;
        valueNode.textContent = value;
        item.appendChild(labelNode);
        item.appendChild(valueNode);
        overview.appendChild(item);
      });
      document.getElementById("backtestSummary").textContent = report.summary || "暂无复盘摘要";
      renderBacktestSummaryTable("backtestHorizonRows", report.by_horizon || [], false);
      renderBacktestSummaryTable("backtestActionRows", report.by_action || [], true);
      renderBacktestSummaryTable("backtestTradePointRows", report.by_trade_point || [], true);
      renderBacktestSummaryTable("backtestStrengthRows", report.by_strength || [], true);
      renderBacktestSummaryTable("backtestTechnicalRows", report.by_technical || [], true);
      renderBacktestSamples(report.samples || []);
      latest = payload || {};
      document.getElementById("json").textContent = JSON.stringify(latest, null, 2);
    }
```

- [ ] **Step 7: Add the async runner**

In `src/astockdata/web_static.py`, add this function before `copyJson()`:

```javascript
    async function runBacktest() {
      const code = document.getElementById("code").value.trim();
      const button = document.getElementById("backtestButton");
      const state = document.getElementById("backtestState");
      button.disabled = true;
      state.textContent = "复盘中，请稍候";
      try {
        const response = await fetch("/api/backtest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, horizons: [5, 10, 20], min_history: 60 })
        });
        const payload = await response.json();
        if (!response.ok) {
          alert(payload.error || "复盘失败");
          return;
        }
        renderBacktest(payload);
        state.textContent = "复盘完成";
      } finally {
        button.disabled = false;
      }
    }
```

- [ ] **Step 8: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
git add src/astockdata/web_static.py tests/test_web.py
git commit -m "feat: render backtest dashboard"
```

## Task 4: Full Verification And Browser QA

**Files:**
- Modify only if verification finds a bug in `src/astockdata/web.py`, `src/astockdata/web_static.py`, or `tests/test_web.py`.

- [ ] **Step 1: Run full unit test suite**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS. The count should include the new `/api/backtest` tests.

- [ ] **Step 2: Start the local Web app**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m astockdata.web --host 127.0.0.1 --port 8000
```

Expected: terminal prints:

```text
Serving Chan signal UI at http://127.0.0.1:8000
```

- [ ] **Step 3: Browser QA the target flow**

The flow under test is: `http://127.0.0.1:8000/` -> enter a stock code -> click `运行复盘` -> backtest dashboard renders summary tables and recent samples without console errors.

Use the in-app Browser runtime. Verify:

- Page identity: URL is `http://127.0.0.1:8000/`, title is `股票交易信号`.
- Not blank: DOM contains `股票交易信号`, `运行复盘`, `信号复盘`.
- Console health: no relevant `error` or `warn` logs.
- Interaction proof:
  - Fill `#code` with a known stock code such as `688630` or `600519`.
  - Click `#backtestButton`.
  - Wait until `#backtestSummary` is no longer `点击“运行复盘”后显示历史信号验证结果。`.
  - Verify `#backtestHorizonRows` has at least one row.
  - Verify `#json` contains `"report"`.
- Screenshot evidence: capture desktop viewport.
- Mobile check: set viewport to `390 x 844`, verify there is no horizontal overflow and the backtest grid is one column.
- Reset viewport before finishing.

- [ ] **Step 4: Fix any QA failures with tests first**

If browser QA finds a bug, write or extend a `tests/test_web.py` assertion before changing production code. Example if `renderBacktest` is missing from the HTML:

```python
        self.assertIn("renderBacktest", body)
```

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: FAIL before the fix, PASS after the fix.

- [ ] **Step 5: Stop the local Web app**

Stop the server with `Ctrl-C` in the running terminal session.

- [ ] **Step 6: Final status check**

Run:

```bash
git status --short --branch
```

Expected: only intentional committed changes remain. `.DS_Store` files may remain untracked and should not be staged.

- [ ] **Step 7: Commit QA fixes if any**

If Task 4 required code changes, run:

```bash
git add src/astockdata/web.py src/astockdata/web_static.py tests/test_web.py
git commit -m "fix: polish backtest dashboard qa"
```

If no code changes were needed, do not create an empty commit.

## Self-Review Checklist

- Spec coverage:
  - Single-stock Web backtest flow: Task 1 and Task 3.
  - Reuse `run_signal_backtest`: Task 1.
  - Web API endpoint: Task 1.
  - Dashboard overview and grouped summaries: Task 2 and Task 3.
  - Recent samples table: Task 2 and Task 3.
  - JSON output: Task 3.
  - Browser QA: Task 4.
- Placeholder scan: no unresolved placeholder markers or open-ended implementation steps are required.
- Type consistency:
  - API response uses top-level `code`, top-level `stock_name`, and nested `report`.
  - Report keys match existing `BacktestReport.to_dict()` fields.
  - JavaScript function names asserted by tests match functions added to `web_static.py`.
