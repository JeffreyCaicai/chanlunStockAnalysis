# 信号回测与验证 V1 设计

## 目标

新增一个轻量级历史回放验证模块，用来衡量当前股票交易信号在历史相似场景中的表现。它不做完整资金曲线和自动交易模拟，第一版只回答：

- 某类信号出现后，未来几个交易日走势是否有利。
- 买入、卖出信号的有利率、平均收益和最差不利波动。
- 一买、二买、三买、一卖、二卖、三卖分别表现如何。
- 信号力度和辅助确认是否真的能区分更可靠的信号。

这个模块的定位是“验证信号质量”，不是“自动生成交易收益报告”。

## 范围

### V1 包含

- 单只股票历史回放。
- 使用已有日线 K 线数据。
- 复用当前 `ChanSignalEngine`、缠论结构、买卖点和技术辅助确认。
- 支持多个观察周期，默认 `5,10,20` 个交易日。
- 输出总体统计、按动作统计、按买卖点统计、按信号力度统计、按辅助确认统计。
- CLI 入口用于快速验证单票。
- JSON 输出用于后续保存和分析。

### V1 不包含

- 资金曲线、复利、手续费、滑点。
- 仓位管理和多股票组合回测。
- 历史大盘/板块环境回测。
- Web 回测大屏。
- 自动挑选最佳参数。

历史市场环境暂不纳入 V1，因为当前市场环境模块读取的是当前大盘和板块数据。如果把它直接套进历史回测，会把今天的环境错误地用于过去日期，形成偷看未来或口径污染。后续可以单独补历史指数和历史板块序列后再加入。

## 回测口径

回测使用滚动历史窗口。在第 N 个交易日生成信号时，系统只能看到第 N 日及以前的 K 线，不能使用未来数据。生成当日信号后，再观察未来 `horizon` 个交易日的表现。

### 买入信号

买入信号包括外部动作 `买入`，对应内部信号可能是 `强买入` 或 `试买入`。

对每个观察周期统计：

- 未来第 `horizon` 日收盘价相对信号日收盘价的涨跌幅。
- 如果涨跌幅大于 0，视为有利。
- 观察期内最低价相对信号日收盘价的跌幅，作为最大不利波动。
- 观察期内最高价相对信号日收盘价的涨幅，作为最大有利波动。

### 卖出信号

卖出信号包括外部动作 `卖出`，对应内部信号可能是 `减仓` 或 `清仓卖出`。

对每个观察周期统计：

- 未来第 `horizon` 日收盘价相对信号日收盘价的反向收益。
- 如果未来收盘价低于信号日收盘价，视为有利。
- 观察期内最高价相对信号日收盘价的涨幅，作为最大不利波动。
- 观察期内最低价相对信号日收盘价的跌幅，作为最大有利波动。

### 继续持有

`继续持有` 第一版只统计出现次数，不纳入有利率。原因是它既可能表示结构健康，也可能表示无明确买卖点，把它和买卖信号混在一起会降低统计可解释性。

## 数据模型

### BacktestSample

表示一条历史信号样本：

- `code`
- `timestamp`
- `action`
- `signal`
- `confidence`
- `strength_label`
- `trade_point_label`
- `technical_label`
- `entry_price`
- `horizon_days`
- `exit_price`
- `return_pct`
- `favorable`
- `max_favorable_pct`
- `max_adverse_pct`

### BacktestBucketSummary

表示某个分组统计：

- `name`
- `sample_count`
- `favorable_count`
- `favorable_rate`
- `average_return_pct`
- `average_max_favorable_pct`
- `average_max_adverse_pct`
- `best_return_pct`
- `worst_return_pct`

### BacktestReport

表示单只股票回测报告：

- `code`
- `start_timestamp`
- `end_timestamp`
- `horizons`
- `sample_count`
- `by_horizon`
- `by_action`
- `by_trade_point`
- `by_strength`
- `by_technical`
- `samples`

## 模块设计

新增 `src/astockdata/backtest.py`。

核心函数：

```python
run_signal_backtest(
    code: str,
    rows: list[KLine],
    horizons: list[int] = [5, 10, 20],
    min_history: int = 60,
) -> BacktestReport
```

执行流程：

1. 从第 `min_history` 根 K 线开始滚动。
2. 对每个日期截取 `rows[:index + 1]`，只使用当日及以前数据。
3. 调用 `analyze_structure` 生成日线结构。
4. 调用 `build_technical_context` 生成辅助确认。
5. 调用 `ChanSignalEngine.evaluate` 生成当日信号。
6. 如果动作是 `买入` 或 `卖出`，对每个观察周期生成样本。
7. 汇总样本，输出分组统计。

第一版不调用 `ChanAnalyzer`，避免在每个历史日期重复请求外部网络数据。回测直接使用已经加载好的历史 K 线。

## CLI 设计

扩展 `astockdata.chan_cli`：

```bash
PYTHONPATH=src python -m astockdata.chan_cli --backtest 600519
```

可选参数：

```bash
PYTHONPATH=src python -m astockdata.chan_cli --backtest 600519 --horizons 5,10,20 --lookback 260
```

输出默认表格：

- 周期
- 分组
- 样本数
- 有利次数
- 有利率
- 平均收益
- 平均最大有利波动
- 平均最大不利波动

JSON 输出复用现有 `--json` 参数，返回完整 `BacktestReport`。

## Web UI 边界

V1 暂不做 Web 回测页。原因是第一版重点是把统计口径和核心数据结构做准。等 CLI 结果稳定后，再把它加入 Web：

- 单票详情里的历史验证摘要。
- CSV 批量列表里的历史胜率列。
- 回测样本明细和可视化图表。

## 错误处理

- K 线数量少于 `min_history + max(horizons)` 时返回空报告，并在 summary 中体现样本不足。
- 如果某个观察周期未来数据不足，则跳过该周期样本。
- 未识别买卖点时，`trade_point_label` 使用 `无明确买卖点`。
- 辅助确认缺失时，`technical_label` 使用 `-`。

## 测试策略

新增 `tests/test_backtest.py`，覆盖：

- 买入样本在未来上涨时计为有利。
- 卖出样本在未来下跌时计为有利。
- 回测不会读取未来 K 线生成当日信号。
- 多周期样本能正确生成。
- 分组统计能正确计算样本数、有利率、平均收益、最差收益。
- K 线不足时返回空统计而不是报错。

更新 CLI 测试，覆盖：

- `--backtest` 参数解析。
- 表格输出包含回测核心列。
- `--json` 输出可被机器读取。

## 后续扩展

V1 稳定后，可以继续扩展：

- 历史大盘和板块环境回测。
- 多股票批量回测。
- 回测结果导出 CSV。
- Web 回测摘要页。
- 参数对比和规则调优。
- 更接近真实交易的资金曲线、手续费、滑点和止损模拟。
