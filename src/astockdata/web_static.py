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
    .analysis-panel, .scanner-panel { min-width: 0; }
    h2 { margin: 0 0 14px; font-size: 16px; }
    label { display: block; margin: 12px 0 6px; color: var(--muted); font-size: 13px; }
    input, textarea, select {
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
    select {
      padding: 8px 9px;
      background: #fff;
    }
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
    tr.active-row { background: #eef6ff; }
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
    .backtest-grid > div {
      min-width: 0;
    }
    .backtest-table-title {
      margin: 10px 0 4px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 650;
    }
    .portfolio-summary {
      color: var(--muted);
      font-size: 13px;
      margin-top: 10px;
    }
    .filter-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 10px 0;
    }
    .filter-grid label { margin: 0; }
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
    .chart-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      margin-top: 6px;
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
    @media (max-width: 1180px) {
      .workbench { grid-template-columns: 280px minmax(420px, 1fr); }
      .scanner-panel { grid-column: 1 / -1; }
    }
    @media (max-width: 760px) {
      .workbench { grid-template-columns: 1fr; }
      .decision-strip { grid-template-columns: 1fr; }
      .explain-grid { grid-template-columns: 1fr; }
      .filter-grid { grid-template-columns: 1fr; }
      .backtest-overview { grid-template-columns: 1fr; }
      .backtest-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>股票交易信号</h1>
    <div id="health">本地服务</div>
  </header>
  <main class="workbench">
    <section class="panel input-panel">
      <h2>输入</h2>
      <label>股票代码或名称</label>
      <input id="code" value="600519" placeholder="例如 002897 或 意华股份">
      <button onclick="analyze()">运行分析</button>
      <button id="backtestButton" class="secondary" onclick="runBacktest()">运行复盘</button>
      <p id="backtestState" class="hint">用历史日K线复盘过去买卖信号，观察5日、10日、20日后的表现。</p>
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
    <section class="panel analysis-panel">
      <h2>研判工作台</h2>
      <div id="decisionStrip" class="decision-strip">
        <div class="decision-card"><span>交易动作</span><strong id="decisionAction">-</strong></div>
        <div class="decision-card"><span>结构方向</span><strong id="decisionStructure">-</strong></div>
        <div class="decision-card"><span>买卖点</span><strong id="decisionPoint">-</strong></div>
        <div class="decision-card"><span>量能换手</span><strong id="decisionVolume">-</strong></div>
        <div class="decision-card"><span>否决条件</span><strong id="decisionVeto">-</strong></div>
        <div class="decision-card"><span>下一步观察</span><strong id="decisionWatch">-</strong></div>
      </div>
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
        <div id="chartLegend" class="chart-legend">标注：最近顶底分型、中枢区间、买卖点、失效价</div>
      </div>
      <h2 style="margin-top:18px">信号复盘</h2>
      <div id="backtestOverview" class="backtest-overview" aria-label="复盘总览">
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
      <h2 style="margin-top:18px">背驰说明</h2>
      <div id="divergenceHelp" class="explain">运行分析后显示背驰提示的白话解释。</div>
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
    </section>
    <section class="panel scanner-panel">
      <h2>交易信号</h2>
      <div id="action" class="signal hold">-</div>
      <div class="kv"><span>内部信号</span><strong id="signal">-</strong></div>
      <div class="kv"><span>风险提示</span><strong id="risk">-</strong></div>
      <h2 style="margin-top:18px">CSV 批量结果</h2>
      <div id="portfolioSummary" class="portfolio-summary">尚未导入 CSV</div>
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
    let portfolioResults = [];
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
    function renderDivergenceHelp(summary) {
      document.getElementById("divergenceHelp").textContent = divergenceText(summary);
    }
    function invalidPrice(signal) {
      const text = ((signal && signal.invalidations) || [])[0] || "";
      const matches = String(text).match(/\d+(?:\.\d+)?/g);
      if (!matches || !matches.length) return null;
      return Number(matches[matches.length - 1]);
    }
    function renderKlineChart(input) {
      const signal = Array.isArray(input) ? { recent_klines: input } : (input || {});
      const svg = document.getElementById("klineChart");
      const meta = document.getElementById("klineChartMeta");
      const legend = document.getElementById("chartLegend");
      const rows = (signal.recent_klines || []).slice(-40);
      svg.innerHTML = "";
      if (!rows.length) {
        meta.textContent = "暂无K线数据";
        legend.textContent = "标注：暂无结构参考线";
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
      const first = rows[0];
      const last = rows[rows.length - 1];
      meta.textContent = first.timestamp + " 到 " + last.timestamp + "，最近收盘 " + fmt(last.close);
      legend.textContent = annotations.length ? "标注：" + Array.from(new Set(annotations)).join(" / ") : "标注：暂无结构参考线";
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
      renderDecisionStrip(latest);
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
      renderKlineChart(latest);
      list("reasons", latest.reasons);
      list("riskNotes", latest.risk_notes);
      list("invalidations", latest.invalidations);
      document.getElementById("json").textContent = JSON.stringify(latest, null, 2);
    }
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
          body: JSON.stringify({ code, horizons: [5, 10, 20], min_history: 60, lookback: 260 })
        });
        const payload = await response.json();
        if (!response.ok) {
          alert(payload.error || "复盘失败");
          state.textContent = "复盘失败，请稍后重试";
          return;
        }
        renderBacktest(payload);
        state.textContent = "复盘完成";
      } catch (error) {
        alert(error && error.message ? error.message : "复盘失败");
        state.textContent = "复盘失败，请稍后重试";
      } finally {
        button.disabled = false;
      }
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
