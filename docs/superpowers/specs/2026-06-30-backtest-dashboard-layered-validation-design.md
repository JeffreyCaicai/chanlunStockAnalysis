# Signal Backtest Dashboard And Layered Validation Design

## Goal

Build a Web backtest dashboard that helps judge whether the current trading signals have worked historically. The first version focuses on one stock at a time, reuses the existing rolling backtest engine, and turns the result into readable layered statistics.

## User Problem

The current app can explain today's stock signal, but the user still needs evidence for whether similar signals were useful before. A signal such as "买入" or "卖出" should not stand alone. The app should show how earlier signals behaved over the next 5, 10, and 20 trading days, and whether the signal quality changes under different structure, strength, and confirmation conditions.

## Scope

### In Scope

- Add a single-stock backtest flow to the existing Web app.
- Reuse `run_signal_backtest` from `src/astockdata/backtest.py`.
- Add a Web API endpoint that accepts a stock code or stock name, resolves it through the existing analyzer flow, fetches daily K-lines, and returns a backtest report.
- Show a dashboard section with:
  - overall sample count and skipped "继续持有" count
  - horizon summaries for 5, 10, and 20 trading days
  - grouped summaries by action, buy/sell point, signal strength, and technical context
  - recent historical signal samples
- Keep the output understandable in Chinese:
  - "胜率" for favorable rate
  - "平均收益"
  - "最大顺向波动"
  - "最大逆向回撤"
- Keep JSON output available for debugging.

### Out Of Scope

- Full market batch backtesting.
- Persisting historical reports to a database.
- Portfolio-level performance curves.
- Transaction costs, slippage, limit-up/limit-down execution modeling.
- Multi-strategy comparison UI.

These are valuable future extensions, but the first version should answer one practical question: "For this stock, has this signal logic worked in the recent historical sample?"

## Current System Context

The project already has the main pieces needed for this feature:

- `src/astockdata/backtest.py` defines `run_signal_backtest`, `BacktestReport`, `BacktestSample`, and bucket summaries.
- `src/astockdata/signals.py` defines `ChanAnalyzer`, signal evaluation, and default data providers.
- `src/astockdata/web.py` serves JSON endpoints and the local HTML page.
- `src/astockdata/web_static.py` renders the current signal workbench, CSV scanner, K-line chart, and JSON panel.

The feature should extend these boundaries rather than create a parallel system.

## Product Design

### Entry Point

Add a "信号复盘" control near the input panel:

- A button labeled "运行复盘"
- A short hint explaining that it uses historical daily K-lines and evaluates past signals over 5, 10, and 20 trading days

The input should use the same `股票代码或名称` field as the current analysis. This avoids asking the user to type the same stock twice.

### Dashboard Layout

Add a "信号复盘" section inside the main workbench. The section should be compact and table-oriented because this is an analytical tool, not a marketing page.

Recommended layout:

1. **复盘总览**
   - 股票代码 / 股票名称 when available
   - date range
   - sample count
   - skipped hold count
   - summary sentence

2. **周期表现**
   - rows: 5日, 10日, 20日
   - columns: 样本数, 胜率, 平均收益, 最大顺向波动, 最大逆向回撤, 最好结果, 最差结果

3. **分层验证**
   - tabs or compact stacked tables for:
     - 动作
     - 买卖点
     - 信号力度
     - 辅助确认
   - each table uses the same columns as the horizon table

4. **最近信号样本**
   - recent rows only, default around 20 rows
   - columns: 日期, 动作, 内部信号, 买卖点, 力度, 辅助, 周期, 入场价, 退出价, 收益, 是否有利

### Empty And Error States

- If there are not enough K-lines, show "样本不足，无法形成可靠回测统计。"
- If no buy/sell signals appear historically, show the backtest summary and an empty table state.
- If the data source fails, show the API error message in a normal alert for the first version.
- If the request is running, disable the button and show "复盘中，请稍候" to avoid duplicate requests.

## API Design

Add:

```text
POST /api/backtest
```

Request:

```json
{
  "code": "688630",
  "horizons": [5, 10, 20],
  "min_history": 60
}
```

Notes:

- `code` may be a stock code or stock name, matching `/api/analyze`.
- `horizons` is optional and defaults to `[5, 10, 20]`.
- `min_history` is optional and defaults to `60`.
- The API should use normalized/resolved code for the actual report.

Response:

```json
{
  "code": "688630",
  "stock_name": "芯碁微装",
  "report": {
    "code": "688630",
    "start_timestamp": "2021-01-04",
    "end_timestamp": "2026-06-30",
    "horizons": [5, 10, 20],
    "sample_count": 123,
    "skipped_hold_count": 456,
    "by_horizon": [],
    "by_action": [],
    "by_trade_point": [],
    "by_strength": [],
    "by_technical": [],
    "samples": [],
    "summary": "共生成123条买卖信号回测样本，跳过456条继续持有信号。"
  }
}
```

The nested `report` keeps compatibility with the existing `BacktestReport.to_dict()`. The top-level `stock_name` is added for Web display.

## Data Flow

1. User enters a stock code or stock name.
2. Web page calls `POST /api/backtest`.
3. API resolves the input with the existing resolver.
4. API fetches daily K-lines from the analyzer's default K-line provider.
5. API calls `run_signal_backtest(resolved_code, rows, horizons, min_history)`.
6. API returns the report and stock identity.
7. Web page renders the overview, layered tables, recent samples, and JSON.

## Layered Validation Meaning

The dashboard should help answer these questions:

- **按周期:** Does the signal work better over 5, 10, or 20 trading days?
- **按动作:** Are buy signals and sell signals both useful, or is only one side reliable?
- **按买卖点:** Are 一买、二买、三买、一卖, etc. performing differently?
- **按力度:** Do stronger signals actually produce better outcomes?
- **按辅助确认:** Does technical context such as "助力" or "拖累" meaningfully change results?

If a bucket has very few samples, the UI should still show it but the user should treat it carefully. The first version does not need statistical significance labels.

## Testing Strategy

### Unit Tests

- Add backtest grouping coverage if a new grouping field is introduced.
- Add Web API tests for:
  - successful `/api/backtest`
  - missing code validation
  - optional horizon parsing
  - stock-name input returning resolved code/name

### Web Static Tests

- Assert the root HTML includes:
  - `运行复盘`
  - `信号复盘`
  - `复盘总览`
  - `周期表现`
  - `分层验证`
  - `最近信号样本`
  - `renderBacktest`
  - `/api/backtest`

### Browser QA

Use the local Web UI:

1. Open the app.
2. Enter a known stock code.
3. Click "运行复盘".
4. Verify the dashboard renders non-empty summary content.
5. Verify the JSON contains the backtest report.
6. Check console errors.
7. Check mobile width for overflow.

## Implementation Notes

- Keep `backtest.py` as the domain/report layer.
- Keep API orchestration in `web.py`.
- Keep page rendering in `web_static.py`.
- Do not change the existing `/api/analyze` behavior.
- Do not change the existing CSV scanner in this iteration.
- Do not add new dependencies.
- Do not delete or rewrite existing signal logic.

## Risks

- Backtesting all available daily rows can be slower than a single current analysis because it repeatedly evaluates historical windows.
- If historical signals are sparse, some buckets may have low sample counts.
- The current backtest is a signal validation tool, not a full execution simulator. It does not model transaction costs, intraday fills, or real liquidity constraints.

## Success Criteria

- A user can enter a stock code or name and run backtest from the Web UI.
- The result clearly shows whether historical signals were favorable over 5, 10, and 20 trading days.
- The user can compare signal quality by action, buy/sell point, strength, and technical context.
- Existing analysis and CSV flows continue to work.
- The full test suite passes.
