# Web Workbench Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the local Web page into a C-mode practical workbench for single-stock review and CSV scanning.

**Architecture:** Keep the current standard-library Web server and static HTML string. Restructure `src/astockdata/web_static.py` into a denser workbench layout, add browser-side state for CSV filters, and enhance the existing SVG K-line renderer with optional structure annotations. Tests remain static HTML/API assertions plus rendered browser smoke checks.

**Tech Stack:** Python `unittest`, static HTML/CSS/JavaScript in `src/astockdata/web_static.py`, existing SVG chart rendering, local standard-library HTTP server.

---

### File Map

- Modify `tests/test_web.py`: assert the workbench shell, decision strip, filters, explanation panels, and chart annotation hooks exist.
- Modify `src/astockdata/web_static.py`: implement the C-mode Web workbench UI and client-side interactions.
- No backend API changes.
- No new JavaScript build tooling or chart dependencies.

### Task 1: Workbench Shell And Decision Strip

**Files:**
- Modify: `tests/test_web.py`
- Modify: `src/astockdata/web_static.py`

- [ ] **Step 1: Write failing static HTML assertions**

In `tests/test_web.py`, extend `test_root_serves_html` with:

```python
        self.assertIn('class="workbench"', body)
        self.assertIn('id="decisionStrip"', body)
        self.assertIn('id="decisionAction"', body)
        self.assertIn('id="decisionStructure"', body)
        self.assertIn('id="decisionPoint"', body)
        self.assertIn('id="decisionVolume"', body)
        self.assertIn('id="decisionVeto"', body)
        self.assertIn('id="decisionWatch"', body)
        self.assertIn("renderDecisionStrip", body)
        self.assertIn("structureDirectionText", body)
        self.assertIn("nextWatchText", body)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: `test_root_serves_html` fails because the workbench shell and decision strip do not exist.

- [ ] **Step 3: Implement the workbench shell**

In `src/astockdata/web_static.py`, change the main layout from a generic `main` grid to a workbench grid:

```html
  <main class="workbench">
    <section class="panel input-panel">
      Keep the existing input, CSV upload, copy JSON, and CSV sample controls here.
    </section>
    <section class="panel analysis-panel">
      Keep structure status, decision strip, K-line chart, structure summary, and explanation panels here.
    </section>
    <section class="panel scanner-panel">
      Keep portfolio summary, CSV filters, portfolio table, trading signal detail fields, and JSON output here.
    </section>
  </main>
```

Add CSS:

```css
    .workbench {
      display: grid;
      grid-template-columns: 300px minmax(460px, 1fr) 420px;
      gap: 16px;
      padding: 16px;
      align-items: start;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-height: 160px;
    }
    .analysis-panel { min-width: 0; }
    .scanner-panel { min-width: 0; }
    .decision-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .decision-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfe;
      min-width: 0;
    }
    .decision-card span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }
    .decision-card strong {
      display: block;
      font-size: 15px;
      overflow-wrap: anywhere;
    }
    @media (max-width: 1180px) {
      .workbench { grid-template-columns: 280px minmax(420px, 1fr); }
      .scanner-panel { grid-column: 1 / -1; }
    }
    @media (max-width: 760px) {
      .workbench { grid-template-columns: 1fr; }
      .decision-strip { grid-template-columns: 1fr; }
    }
```

Add the decision strip at the top of the analysis panel:

```html
      <h2>研判工作台</h2>
      <div id="decisionStrip" class="decision-strip">
        <div class="decision-card"><span>交易动作</span><strong id="decisionAction">-</strong></div>
        <div class="decision-card"><span>结构方向</span><strong id="decisionStructure">-</strong></div>
        <div class="decision-card"><span>买卖点</span><strong id="decisionPoint">-</strong></div>
        <div class="decision-card"><span>量能换手</span><strong id="decisionVolume">-</strong></div>
        <div class="decision-card"><span>否决条件</span><strong id="decisionVeto">-</strong></div>
        <div class="decision-card"><span>下一步观察</span><strong id="decisionWatch">-</strong></div>
      </div>
```

- [ ] **Step 4: Implement decision strip helpers**

Add JavaScript helpers before `renderSignal`:

```javascript
    function structureDirectionText(signal) {
      if (!signal || !signal.daily_summary) return "-";
      const summary = signal.daily_summary;
      const zone = summary.latest_zone;
      const parts = [summary.trend_label || "-"];
      if (zone && zone.position_label) parts.push(zone.position_label);
      return parts.filter(Boolean).join(" / ");
    }

    function nextWatchText(signal) {
      if (!signal) return "-";
      const invalidation = (signal.invalidations || [])[0];
      if (invalidation) return invalidation;
      const zone = signal.daily_summary && signal.daily_summary.latest_zone;
      if (zone && zone.meaning) return zone.meaning;
      const point = signal.trade_point;
      if (point && point.invalidation && point.invalidation !== "-") return point.invalidation;
      return "等待更明确的结构确认";
    }

    function renderDecisionStrip(signal) {
      document.getElementById("decisionAction").textContent = signal.action || "-";
      document.getElementById("decisionStructure").textContent = structureDirectionText(signal);
      document.getElementById("decisionPoint").textContent = tradePointText(signal.trade_point);
      document.getElementById("decisionVolume").textContent = volumeContextText(signal.volume_context);
      document.getElementById("decisionVeto").textContent = vetoContextText(signal.veto_context);
      document.getElementById("decisionWatch").textContent = nextWatchText(signal);
    }
```

Call `renderDecisionStrip(latest);` inside `renderSignal`.

- [ ] **Step 5: Run test to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: Web tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/astockdata/web_static.py tests/test_web.py
git commit -m "feat: add web workbench decision strip"
```

### Task 2: CSV Filters And Explanation Panels

**Files:**
- Modify: `tests/test_web.py`
- Modify: `src/astockdata/web_static.py`

- [ ] **Step 1: Write failing static HTML assertions**

In `tests/test_web.py`, extend `test_root_serves_html` with:

```python
        self.assertIn('id="filterAction"', body)
        self.assertIn('id="filterVeto"', body)
        self.assertIn('id="filterVolume"', body)
        self.assertIn("filterPortfolioResults", body)
        self.assertIn("setActivePortfolioRow", body)
        self.assertIn('id="riskNotes"', body)
        self.assertIn('class="explain-grid"', body)
        self.assertIn("没有符合筛选条件的股票", body)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: `test_root_serves_html` fails because filters and explanation panels are missing.

- [ ] **Step 3: Add CSV filter controls**

In the scanner panel above the table, add:

```html
      <div class="filter-grid">
        <label>动作
          <select id="filterAction" onchange="renderPortfolio()">
            <option value="all">全部</option>
            <option value="买入">买入</option>
            <option value="卖出">卖出</option>
            <option value="继续持有">继续持有</option>
          </select>
        </label>
        <label>否决
          <select id="filterVeto" onchange="renderPortfolio()">
            <option value="all">全部</option>
            <option value="vetoed">只看已否决</option>
            <option value="clear">排除已否决</option>
          </select>
        </label>
        <label>量能
          <select id="filterVolume" onchange="renderPortfolio()">
            <option value="all">全部</option>
            <option value="助力">助力</option>
            <option value="蓄势">蓄势</option>
            <option value="拖累">拖累</option>
          </select>
        </label>
      </div>
```

Add CSS:

```css
    .filter-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 10px 0;
    }
    .filter-grid label { margin: 0; }
    select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      background: #fff;
      font: inherit;
    }
    tr.active-row { background: #eef6ff; }
```

- [ ] **Step 4: Add explanation panels**

Replace the separate reasons/risk/invalidations layout with:

```html
      <h2 style="margin-top:18px">解释与风险</h2>
      <div class="explain-grid">
        <div>
          <h3>关键原因</h3>
          <ul id="reasons"></ul>
        </div>
        <div>
          <h3>风险提示</h3>
          <ul id="riskNotes"></ul>
        </div>
        <div>
          <h3>失效条件</h3>
          <ul id="invalidations"></ul>
        </div>
      </div>
```

Add CSS:

```css
    .explain-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }
    .explain-grid h3 {
      margin: 0 0 6px;
      font-size: 13px;
    }
    .explain-grid > div {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfe;
      min-width: 0;
    }
    @media (max-width: 760px) {
      .explain-grid { grid-template-columns: 1fr; }
      .filter-grid { grid-template-columns: 1fr; }
    }
```

Update `renderSignal` to call:

```javascript
      list("reasons", latest.reasons);
      list("riskNotes", latest.risk_notes);
      list("invalidations", latest.invalidations);
```

- [ ] **Step 5: Implement browser-side portfolio filtering**

Add state and helpers near `let latest = {};`:

```javascript
    let portfolioResults = [];

    function filterPortfolioResults(results) {
      const action = document.getElementById("filterAction").value;
      const veto = document.getElementById("filterVeto").value;
      const volume = document.getElementById("filterVolume").value;
      return (results || []).filter((item) => {
        const actionOk = action === "all" || item.action === action;
        const vetoed = Boolean(item.veto_context && item.veto_context.vetoed);
        const vetoOk = veto === "all" || (veto === "vetoed" && vetoed) || (veto === "clear" && !vetoed);
        const volumeOk = volume === "all" || (item.volume_context && item.volume_context.label === volume);
        return actionOk && vetoOk && volumeOk;
      });
    }

    function setActivePortfolioRow(row) {
      document.querySelectorAll("#portfolioRows tr").forEach((item) => item.classList.remove("active-row"));
      if (row) row.classList.add("active-row");
    }
```

Change `renderPortfolio(results)` to:

```javascript
    function renderPortfolio(results) {
      if (Array.isArray(results)) portfolioResults = results;
      const rows = document.getElementById("portfolioRows");
      rows.innerHTML = "";
      const total = portfolioResults.length;
      const filtered = filterPortfolioResults(portfolioResults);
      const counts = { "买入": 0, "卖出": 0, "继续持有": 0 };
      portfolioResults.forEach((item) => counts[item.action] = (counts[item.action] || 0) + 1);
      filtered.forEach((item) => {
        const row = document.createElement("tr");
        [displayIdentity(item), item.action, item.signal, tradePointText(item.trade_point), marketContextText(item.market_context), technicalContextText(item.technical_context), volumeContextText(item.volume_context), vetoContextText(item.veto_context), item.strength_label || fmt(item.confidence), item.confirmation_status || "-"].forEach((value) => {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.appendChild(cell);
        });
        row.addEventListener("click", () => {
          renderSignal(item);
          setActivePortfolioRow(row);
        });
        rows.appendChild(row);
      });
      if (total && !filtered.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.colSpan = 10;
        cell.textContent = "没有符合筛选条件的股票";
        row.appendChild(cell);
        rows.appendChild(row);
      }
      document.getElementById("portfolioSummary").textContent = total
        ? "共 " + total + " 只，当前显示 " + filtered.length + " 只：买入 " + (counts["买入"] || 0) + "，卖出 " + (counts["卖出"] || 0) + "，继续持有 " + (counts["继续持有"] || 0)
        : "尚未导入 CSV";
    }
```

- [ ] **Step 6: Run test to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: Web tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/astockdata/web_static.py tests/test_web.py
git commit -m "feat: add web portfolio filters"
```

### Task 3: K-Line Structure Annotations

**Files:**
- Modify: `tests/test_web.py`
- Modify: `src/astockdata/web_static.py`

- [ ] **Step 1: Write failing static HTML assertions**

In `tests/test_web.py`, extend `test_root_serves_html` with:

```python
        self.assertIn('id="chartLegend"', body)
        self.assertIn("invalidPrice", body)
        self.assertIn("drawPriceLine", body)
        self.assertIn("drawMarker", body)
        self.assertIn("中枢上沿", body)
        self.assertIn("失效价", body)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: `test_root_serves_html` fails because chart annotations are missing.

- [ ] **Step 3: Add chart legend container**

Under `klineChartMeta`, add:

```html
        <div id="chartLegend" class="chart-legend">标注：最近顶底分型、中枢区间、买卖点、失效价</div>
```

Add CSS:

```css
    .chart-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      margin-top: 6px;
    }
```

- [ ] **Step 4: Add invalidation price helper**

Add before `renderKlineChart`:

```javascript
    function invalidPrice(signal) {
      const text = ((signal && signal.invalidations) || [])[0] || "";
      const matches = String(text).match(/\\d+(?:\\.\\d+)?/g);
      if (!matches || !matches.length) return null;
      return Number(matches[matches.length - 1]);
    }
```

- [ ] **Step 5: Enhance `renderKlineChart`**

Change the function signature to accept a signal:

```javascript
    function renderKlineChart(input) {
      const signal = Array.isArray(input) ? { recent_klines: input } : (input || {});
      const svg = document.getElementById("klineChart");
      const meta = document.getElementById("klineChartMeta");
      const legend = document.getElementById("chartLegend");
      const rows = (signal.recent_klines || []).slice(-40);
```

Inside the function after `add` is defined, add helpers:

```javascript
      const annotations = [];
      function drawPriceLine(price, label, color, dash) {
        if (price === null || price === undefined || Number.isNaN(Number(price))) return;
        const value = Number(price);
        if (value < minPrice || value > maxPrice) return;
        const yy = y(value);
        add("line", { x1: pad.left, y1: yy, x2: width - pad.right, y2: yy, stroke: color, "stroke-width": "1.2", "stroke-dasharray": dash || "4 4" });
        const text = add("text", { x: width - pad.right - 118, y: yy - 4, fill: color, "font-size": "11" });
        text.textContent = label + " " + value.toFixed(2);
        annotations.push(label);
      }

      function drawMarker(point, label, color) {
        if (!point || point.price === null || point.price === undefined) return;
        const index = rows.findIndex((row) => String(point.timestamp || "").startsWith(row.timestamp));
        if (index < 0) return;
        const x = pad.left + step * index + step / 2;
        const yy = y(Number(point.price));
        add("circle", { cx: x, cy: yy, r: "4", fill: color });
        const text = add("text", { x: x + 6, y: yy - 6, fill: color, "font-size": "11" });
        text.textContent = label;
        annotations.push(label);
      }
```

After drawing candles, add:

```javascript
      const summary = signal.daily_summary || {};
      const zone = summary.latest_zone;
      if (zone) {
        drawPriceLine(zone.high, "中枢上沿", "#1769aa", "5 4");
        drawPriceLine(zone.low, "中枢下沿", "#1769aa", "5 4");
      }
      drawMarker(summary.latest_top, "顶分型", "#b42318");
      drawMarker(summary.latest_bottom, "底分型", "#0f8a5f");
      if (signal.trade_point) drawPriceLine(signal.trade_point.price, signal.trade_point.label || "买卖点", "#805600", "3 3");
      drawPriceLine(invalidPrice(signal), "失效价", "#b42318", "2 3");
```

Replace the meta/legend update with:

```javascript
      meta.textContent = first.timestamp + " 到 " + last.timestamp + "，最近收盘 " + fmt(last.close);
      legend.textContent = annotations.length ? "标注：" + Array.from(new Set(annotations)).join(" / ") : "标注：暂无结构参考线";
```

Change `renderSignal` to call:

```javascript
      renderKlineChart(latest);
```

- [ ] **Step 6: Run test to verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_web -v
```

Expected: Web tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/astockdata/web_static.py tests/test_web.py
git commit -m "feat: annotate web kline chart"
```

### Task 4: Verification And Browser QA

**Files:**
- No new source files.

- [ ] **Step 1: Run full unit tests**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Start local Web server**

Run:

```bash
PYTHONPATH=src .venv/bin/python -m astockdata.web --host 127.0.0.1 --port 8000
```

Expected: server prints `Serving Chan signal UI at http://127.0.0.1:8000` and keeps running.

- [ ] **Step 3: Browser desktop smoke**

Use the Browser plugin against `http://127.0.0.1:8000`.

Check:

- Page title is `股票交易信号`.
- DOM contains `decisionStrip`, `filterAction`, `klineChart`, and `chartLegend`.
- No framework error overlay appears.
- Browser console has no relevant errors.
- Desktop screenshot shows the workbench without obvious overlap.

- [ ] **Step 4: Browser interaction smoke**

In the browser:

1. Fill the stock input with `603337`.
2. Click `运行分析`.
3. Wait for the result.
4. Confirm `decisionAction` is not `-`.
5. Confirm `chartLegend` updates.
6. Confirm JSON contains the same code.

Expected: the app renders a real analysis result and the workbench updates.

- [ ] **Step 5: Browser mobile smoke**

Set viewport around 390px wide and reload.

Check:

- Panels stack vertically.
- Decision cards fit without text overlap.
- Inputs and buttons fit their containers.
- The chart remains visible.

- [ ] **Step 6: Review git status**

Run:

```bash
git status --short --branch
git log --oneline --decorate -8
```

Expected: only `.DS_Store` and ignored `.superpowers/` are outside committed code changes.
