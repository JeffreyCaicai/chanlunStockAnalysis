INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>股票交易信号</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #657080;
      --line: #d9dee7;
      --accent: #1769aa;
      --buy: #0f8a5f;
      --sell: #b42318;
      --hold: #805600;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { margin: 0; font-size: 20px; font-weight: 700; }
    main {
      display: grid;
      grid-template-columns: 280px minmax(360px, 1fr) 360px;
      gap: 16px;
      padding: 16px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-height: 160px;
    }
    h2 { margin: 0 0 14px; font-size: 16px; }
    label { display: block; margin: 12px 0 6px; color: var(--muted); font-size: 13px; }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
      background: #fff;
    }
    button {
      margin-top: 14px;
      width: 100%;
      border: 0;
      border-radius: 6px;
      padding: 10px 12px;
      background: var(--accent);
      color: #fff;
      font-weight: 650;
      cursor: pointer;
    }
    button.secondary { background: #374151; }
    .signal {
      font-size: 28px;
      font-weight: 800;
      margin: 10px 0 4px;
    }
    .buy { color: var(--buy); }
    .sell { color: var(--sell); }
    .hold { color: var(--hold); }
    .kv {
      display: grid;
      grid-template-columns: 110px 1fr;
      gap: 8px;
      padding: 8px 0;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
    }
    .kv span:first-child { color: var(--muted); }
    .strength-box {
      display: flex;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 8px;
    }
    .inline-hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px 14px;
      font-size: 13px;
    }
    .summary-grid div {
      border-bottom: 1px solid var(--line);
      padding: 6px 0;
      min-width: 0;
    }
    .summary-grid span {
      display: block;
      color: var(--muted);
      margin-bottom: 2px;
    }
    .summary-grid strong {
      display: block;
      overflow-wrap: anywhere;
    }
    .sample {
      background: #f8fafc;
      border: 1px solid var(--line);
      color: var(--text);
      margin-top: 10px;
      max-height: none;
      white-space: pre-wrap;
    }
    .hint {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.55;
      margin: 8px 0 0;
    }
    .table-wrap {
      overflow: auto;
      margin-top: 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      white-space: nowrap;
    }
    tbody tr { cursor: pointer; }
    tbody tr:hover { background: #f8fafc; }
    .portfolio-summary {
      color: var(--muted);
      font-size: 13px;
      margin-top: 10px;
    }
    .chart-box {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fbfcfe;
      padding: 10px;
    }
    #klineChart {
      display: block;
      width: 100%;
      height: 180px;
    }
    .explain {
      border-left: 3px solid var(--accent);
      background: #f8fafc;
      padding: 10px 12px;
      border-radius: 6px;
      color: var(--text);
      font-size: 13px;
      line-height: 1.6;
    }
    ul { padding-left: 20px; margin: 8px 0; }
    pre {
      overflow: auto;
      background: #0f172a;
      color: #e5e7eb;
      border-radius: 6px;
      padding: 12px;
      max-height: 280px;
      font-size: 12px;
    }
    @media (max-width: 980px) {
      main { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>股票交易信号</h1>
    <div id="health">本地服务</div>
  </header>
  <main>
    <section>
      <h2>输入</h2>
      <label>股票代码或名称</label>
      <input id="code" value="600519" placeholder="例如 002897 或 意华股份">
      <button onclick="analyze()">运行分析</button>
      <label>导入股票 CSV</label>
      <input id="csvFile" type="file" accept=".csv,text/csv">
      <button class="secondary" onclick="analyzePortfolio()">分析 CSV 列表</button>
      <button class="secondary" onclick="copyJson()">复制 JSON</button>
      <div id="copyState" class="hint"></div>
      <h2 style="margin-top:18px">CSV 示例</h2>
      <pre class="sample">code
603337
600519
000001</pre>
      <p class="hint">只需要一列 code。每行一个股票代码或名称，用来批量扫描走势和信号。</p>
    </section>
    <section>
      <h2>结构状态</h2>
      <div class="kv"><span>股票</span><strong id="stockIdentity">-</strong></div>
      <div class="kv"><span>确认状态</span><strong id="confirmed">-</strong></div>
      <div class="kv"><span>30分钟确认</span><strong id="confirmation">-</strong></div>
      <div class="kv"><span>信号力度</span><div class="strength-box"><strong id="strength">-</strong><span id="strengthHint" class="inline-hint">运行分析后显示白话解释</span></div></div>
      <div class="kv"><span>买卖点</span><div class="strength-box"><strong id="tradePoint">-</strong><span id="tradePointDetail" class="inline-hint">运行分析后显示买卖点解释</span></div></div>
      <div class="kv"><span>市场环境</span><div class="strength-box"><strong id="marketContext">-</strong><span id="marketContextDetail" class="inline-hint">运行分析后显示大盘和板块环境</span></div></div>
      <div class="kv"><span>辅助确认</span><div class="strength-box"><strong id="technicalContext">-</strong><span id="technicalContextDetail" class="inline-hint">运行分析后显示趋势动量和布林状态</span></div></div>
      <div class="kv"><span>量能换手</span><div class="strength-box"><strong id="volumeContext">-</strong><span id="volumeContextDetail" class="inline-hint">运行分析后显示成交量和换手状态</span></div></div>
      <div class="kv"><span>否决条件</span><div class="strength-box"><strong id="vetoStatus">-</strong><span id="vetoDetail" class="inline-hint">运行分析后显示是否有买入否决</span></div></div>
      <div class="kv"><span>复盘摘要</span><strong id="tradePointReplay">-</strong></div>
      <h2 style="margin-top:18px">结构摘要</h2>
      <div id="structureSummary" class="summary-grid"></div>
      <h2 style="margin-top:18px">最近K线走势</h2>
      <div class="chart-box">
        <svg id="klineChart" viewBox="0 0 640 220" role="img" aria-label="最近日线K线走势"></svg>
        <div id="klineChartMeta" class="hint">运行分析后显示最近日线。</div>
      </div>
      <h2 style="margin-top:18px">背驰说明</h2>
      <div id="divergenceHelp" class="explain">运行分析后显示背驰提示的白话解释。</div>
      <h2 style="margin-top:18px">原因</h2>
      <ul id="reasons"></ul>
      <h2 style="margin-top:18px">失效条件</h2>
      <ul id="invalidations"></ul>
    </section>
    <section>
      <h2>交易信号</h2>
      <div id="action" class="signal hold">-</div>
      <div class="kv"><span>内部信号</span><strong id="signal">-</strong></div>
      <div class="kv"><span>风险提示</span><strong id="risk">-</strong></div>
      <h2 style="margin-top:18px">CSV 批量结果</h2>
      <div id="portfolioSummary" class="portfolio-summary">尚未导入 CSV</div>
      <div class="table-wrap">
        <table id="portfolioTable">
          <thead>
            <tr>
              <th>股票</th>
              <th>动作</th>
              <th>内部信号</th>
              <th>买卖点</th>
              <th>环境</th>
              <th>辅助</th>
              <th>量能</th>
              <th>否决</th>
              <th>力度</th>
              <th>30分钟</th>
            </tr>
          </thead>
          <tbody id="portfolioRows"></tbody>
        </table>
      </div>
      <h2 style="margin-top:18px">JSON</h2>
      <pre id="json">{}</pre>
    </section>
  </main>
  <script>
    let latest = {};
    function list(id, items) {
      const node = document.getElementById(id);
      node.innerHTML = "";
      (items || []).forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        node.appendChild(li);
      });
    }
    function fmt(value) {
      if (value === null || value === undefined || value === "") return "-";
      if (typeof value === "number") return value.toFixed(2);
      return String(value);
    }
    function displayIdentity(signal) {
      if (!signal) return "-";
      return signal.stock_name ? signal.stock_name + "（" + signal.code + "）" : signal.code;
    }
    function pointText(point) {
      if (!point) return "-";
      return point.timestamp + " / " + fmt(point.price);
    }
    function strokeText(stroke) {
      if (!stroke) return "-";
      return stroke.direction_label + " " + stroke.start_timestamp + " -> " + stroke.end_timestamp + "，幅度 " + fmt(stroke.amplitude);
    }
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
    function divergenceText(summary) {
      if (!summary) return "运行分析后显示背驰提示的白话解释。";
      if (summary.up_divergence_risk) {
        return "上行背驰风险：价格仍在尝试向上，但最近一段上涨的力度比前一段弱，说明买盘跟进可能变慢。它不是“马上卖出”的意思，更像是提醒：不要盲目追高，最好等回调或新的买点确认。";
      }
      if (summary.down_divergence_repair) {
        return "下行背驰修复：价格还在弱势区，但最近一段下跌力度变小，说明空方力量可能减弱。它不是“马上买入”的意思，更像是提醒：可以开始观察止跌和反弹确认。";
      }
      return "当前简化模型没有识别到明显背驰。可以重点看趋势、最近顶底分型，以及价格是否触发失效条件。";
    }
    function strengthExplanation(signal) {
      if (!signal || signal.confidence === undefined || signal.confidence === null) {
        return "运行分析后显示这次信号有多扎实。";
      }
      const score = Number(signal.confidence) || 0;
      const missingConfirm = signal.confirmation_missing || signal.confirmation_status === "缺失";
      if (signal.action === "买入") {
        if (score >= 0.72) {
          return "买入依据较充分，日线结构和确认条件配合较好。";
        }
        if (missingConfirm) {
          return "有买入迹象，但30分钟确认不足，更适合轻仓试探或继续等确认。";
        }
        return "有买入迹象，但力度一般，先控制仓位。";
      }
      if (signal.action === "卖出") {
        if (score >= 0.72) {
          return "风险信号较明确，优先考虑减仓或离场。";
        }
        return "风险开始抬头，适合收紧止损并降低仓位。";
      }
      if (score >= 0.6) {
        return "结构没有明显破坏，但买卖点还不够清晰。";
      }
      return "当前信号不够扎实，主要价值是继续观察。";
    }
    function tradePointText(point) {
      if (!point) return "-";
      return point.label || "-";
    }
    function tradePointDetail(point) {
      if (!point || !point.explanation) return "当前没有明确买卖点。";
      const price = point.price ? " 参考价 " + fmt(point.price) + "。" : "";
      return point.explanation + price;
    }
    function replayText(replay) {
      if (!replay) return "-";
      return replay.summary || "-";
    }
    function marketContextText(context) {
      if (!context) return "-";
      return context.label || "-";
    }
    function marketContextDetail(context) {
      if (!context) return "市场环境数据暂不可用。";
      return context.summary || "市场环境数据暂不可用。";
    }
    function technicalContextText(context) {
      if (!context) return "-";
      return context.label || "-";
    }
    function technicalContextDetail(context) {
      if (!context) return "技术辅助数据暂不可用。";
      return context.summary || "技术辅助数据暂不可用。";
    }
    function volumeContextText(context) {
      if (!context) return "-";
      return context.volume_label || context.label || "-";
    }
    function volumeContextDetail(context) {
      if (!context) return "量能数据暂不可用。";
      return context.summary || "量能数据暂不可用。";
    }
    function vetoContextText(context) {
      if (!context || !context.vetoed) return "未触发";
      return "已否决买入";
    }
    function vetoContextDetail(context) {
      if (!context) return "未触发买入否决条件。";
      return context.summary || "未触发买入否决条件。";
    }
    function renderDivergenceHelp(summary) {
      document.getElementById("divergenceHelp").textContent = divergenceText(summary);
    }
    function renderKlineChart(candles) {
      const svg = document.getElementById("klineChart");
      const meta = document.getElementById("klineChartMeta");
      const rows = (candles || []).slice(-40);
      svg.innerHTML = "";
      if (!rows.length) {
        meta.textContent = "暂无K线数据";
        return;
      }
      const width = 640;
      const height = 220;
      const pad = { left: 44, right: 14, top: 12, bottom: 26 };
      const highs = rows.map(row => row.high);
      const lows = rows.map(row => row.low);
      const maxPrice = Math.max(...highs);
      const minPrice = Math.min(...lows);
      const span = Math.max(maxPrice - minPrice, 0.01);
      const plotW = width - pad.left - pad.right;
      const plotH = height - pad.top - pad.bottom;
      const step = plotW / rows.length;
      const candleW = Math.max(3, Math.min(10, step * 0.56));
      const y = price => pad.top + (maxPrice - price) / span * plotH;
      const ns = "http://www.w3.org/2000/svg";
      const add = (tag, attrs) => {
        const node = document.createElementNS(ns, tag);
        Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
        svg.appendChild(node);
        return node;
      };
      [maxPrice, (maxPrice + minPrice) / 2, minPrice].forEach(price => {
        const yy = y(price);
        add("line", { x1: pad.left, y1: yy, x2: width - pad.right, y2: yy, stroke: "#e5e7eb", "stroke-width": "1" });
        const text = add("text", { x: 4, y: yy + 4, fill: "#657080", "font-size": "11" });
        text.textContent = price.toFixed(2);
      });
      rows.forEach((row, index) => {
        const x = pad.left + step * index + step / 2;
        const up = row.close >= row.open;
        const color = up ? "#b42318" : "#0f8a5f";
        const openY = y(row.open);
        const closeY = y(row.close);
        const bodyTop = Math.min(openY, closeY);
        const bodyH = Math.max(Math.abs(openY - closeY), 2);
        add("line", { x1: x, y1: y(row.high), x2: x, y2: y(row.low), stroke: color, "stroke-width": "1.4" });
        add("rect", { x: x - candleW / 2, y: bodyTop, width: candleW, height: bodyH, fill: color, rx: "1" });
      });
      const first = rows[0];
      const last = rows[rows.length - 1];
      meta.textContent = first.timestamp + " 到 " + last.timestamp + "，最近收盘 " + fmt(last.close);
    }
    function setSummary(items) {
      const node = document.getElementById("structureSummary");
      node.innerHTML = "";
      items.forEach(([label, value]) => {
        const item = document.createElement("div");
        const labelNode = document.createElement("span");
        const valueNode = document.createElement("strong");
        labelNode.textContent = label;
        valueNode.textContent = value || "-";
        item.appendChild(labelNode);
        item.appendChild(valueNode);
        node.appendChild(item);
      });
    }
    function renderStructure(signal) {
      const summary = signal.daily_summary || {};
      setSummary([
        ["数据日期", fmt(summary.latest_timestamp)],
        ["最新价", fmt(summary.latest_price)],
        ["日线趋势", fmt(summary.trend_label)],
        ["结构数量", fmt(summary.fractal_count) + " 分型 / " + fmt(summary.stroke_count) + " 笔"],
        ["最近顶分型", pointText(summary.latest_top)],
        ["最近底分型", pointText(summary.latest_bottom)],
        ["最近一笔", strokeText(summary.latest_stroke)],
        ["最近中枢", zoneText(summary.latest_zone)],
        ["中枢位置", zonePositionText(summary.latest_zone)],
        ["结构含义", zoneMeaningText(summary.latest_zone)],
        ["背驰提示", summary.up_divergence_risk ? "上行背驰风险" : (summary.down_divergence_repair ? "下行背驰修复" : "-")]
      ]);
      renderDivergenceHelp(summary);
    }
    function renderPortfolio(results) {
      const rows = document.getElementById("portfolioRows");
      rows.innerHTML = "";
      const total = (results || []).length;
      const counts = { "买入": 0, "卖出": 0, "继续持有": 0 };
      (results || []).forEach((item, index) => {
        counts[item.action] = (counts[item.action] || 0) + 1;
        const row = document.createElement("tr");
        [displayIdentity(item), item.action, item.signal, tradePointText(item.trade_point), marketContextText(item.market_context), technicalContextText(item.technical_context), volumeContextText(item.volume_context), vetoContextText(item.veto_context), item.strength_label || fmt(item.confidence), item.confirmation_status || "-"].forEach((value) => {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.appendChild(cell);
        });
        row.addEventListener("click", () => renderSignal(results[index]));
        rows.appendChild(row);
      });
      document.getElementById("portfolioSummary").textContent = total
        ? "共 " + total + " 只：买入 " + (counts["买入"] || 0) + "，卖出 " + (counts["卖出"] || 0) + "，继续持有 " + (counts["继续持有"] || 0)
        : "尚未导入 CSV";
    }
    async function analyze() {
      const code = document.getElementById("code").value.trim();
      const payload = { code };
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      latest = await response.json();
      if (!response.ok) {
        alert(latest.error || "分析失败");
        return;
      }
      renderSignal(latest);
      renderPortfolio([]);
    }
    function parseCsv(text) {
      const lines = text.trim().replace(/^\\uFEFF/, "").split(/\\r?\\n/);
      const headers = lines.shift().split(",").map(s => s.trim());
      return lines.filter(Boolean).map(line => {
        const values = line.split(",").map(s => s.trim());
        const row = {};
        headers.forEach((header, index) => row[header] = values[index]);
        const item = { code: row.code };
        if (row.cost !== undefined && row.cost !== "") item.cost = Number(row.cost);
        if (row.position !== undefined && row.position !== "") item.position = Number(row.position);
        return item;
      });
    }
    async function analyzePortfolio() {
      const file = document.getElementById("csvFile").files[0];
      if (!file) {
        alert("请选择 CSV 文件");
        return;
      }
      const holdings = parseCsv(await file.text());
      const response = await fetch("/api/analyze-portfolio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ holdings })
      });
      const payload = await response.json();
      if (!response.ok) {
        alert(payload.error || "分析失败");
        return;
      }
      latest = payload;
      if (payload.results && payload.results.length) {
        renderSignal(payload.results[0]);
      }
      renderPortfolio(payload.results || []);
      document.getElementById("json").textContent = JSON.stringify(payload, null, 2);
    }
    function renderSignal(signal) {
      latest = signal;
      document.getElementById("action").textContent = latest.action;
      document.getElementById("action").className =
        "signal " + (latest.action === "买入" ? "buy" : latest.action === "卖出" ? "sell" : "hold");
      document.getElementById("signal").textContent = latest.signal;
      document.getElementById("stockIdentity").textContent = displayIdentity(latest);
      document.getElementById("confirmed").textContent = latest.confirmed ? "正式信号" : "盘中预警";
      document.getElementById("confirmation").textContent = latest.confirmation_status || (latest.confirmation_missing ? "缺失，已降级" : "可用");
      document.getElementById("strength").textContent = (latest.strength_label || "-") + "（原始分 " + latest.confidence + "）";
      document.getElementById("strengthHint").textContent = strengthExplanation(latest);
      document.getElementById("tradePoint").textContent = tradePointText(latest.trade_point);
      document.getElementById("tradePointDetail").textContent = tradePointDetail(latest.trade_point);
      document.getElementById("marketContext").textContent = marketContextText(latest.market_context);
      document.getElementById("marketContextDetail").textContent = marketContextDetail(latest.market_context);
      document.getElementById("technicalContext").textContent = technicalContextText(latest.technical_context);
      document.getElementById("technicalContextDetail").textContent = technicalContextDetail(latest.technical_context);
      document.getElementById("volumeContext").textContent = volumeContextText(latest.volume_context);
      document.getElementById("volumeContextDetail").textContent = volumeContextDetail(latest.volume_context);
      document.getElementById("vetoStatus").textContent = vetoContextText(latest.veto_context);
      document.getElementById("vetoDetail").textContent = vetoContextDetail(latest.veto_context);
      document.getElementById("tradePointReplay").textContent = replayText(latest.trade_point_replay);
      document.getElementById("risk").textContent = (latest.risk_notes || []).join("；") || "-";
      renderStructure(latest);
      renderKlineChart(latest.recent_klines);
      list("reasons", latest.reasons);
      list("invalidations", latest.invalidations);
      document.getElementById("json").textContent = JSON.stringify(latest, null, 2);
    }
    async function copyJson() {
      try {
        await navigator.clipboard.writeText(JSON.stringify(latest, null, 2));
        document.getElementById("copyState").textContent = "已复制 JSON";
      } catch (error) {
        document.getElementById("copyState").textContent = "复制失败，请手动复制 JSON";
      }
    }
    fetch("/api/health").then(r => r.json()).then(data => {
      document.getElementById("health").textContent = data.status === "ok" ? "服务正常" : "服务异常";
    });
  </script>
</body>
</html>
"""
