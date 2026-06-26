# 本地 A 股分析工具

这个仓库上游主要提供 `SKILL.md` 里的数据端点代码。本地已经补了一层可执行 Python 包，把稳定的 HTTP 数据源整理成 CLI 和可测试模块。

## 当前范围

第一版只使用当前环境验证稳定的数据源：

- 腾讯财经：实时价、PE(TTM)、PB、市值、换手率、涨跌停。
- 东财 push2：行业、股本、市值、上市日期。
- 东财 reportapi：个股研报、机构评级、未来 EPS 预测。

暂不把 `mootdx` 放进默认流程。原因是它依赖通达信 TCP 7709，在当前网络下服务器握手后会 reset。它后续可以作为国内网络环境下的增强行情源。

## 安装

```bash
cd /Users/jeffrey/Desktop/tufaqixiang/astockdata
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

如果只想用已经建好的本地环境：

```bash
cd /Users/jeffrey/Desktop/tufaqixiang/astockdata
source .venv/bin/activate
```

## 使用

单票分析：

```bash
PYTHONPATH=src python -m astockdata.cli 600519
```

批量对比：

```bash
PYTHONPATH=src python -m astockdata.cli 600519 688017 000858
```

输出 JSON，方便接入后续策略或笔记系统：

```bash
PYTHONPATH=src python -m astockdata.cli 600519 688017 --json
```

多拉几页研报，但只用最新 20 篇来聚合 EPS：

```bash
PYTHONPATH=src python -m astockdata.cli 688017 --report-pages 2
```

调整 EPS 聚合使用的最新研报数量：

```bash
PYTHONPATH=src python -m astockdata.cli 688017 --report-pages 2 --max-reports 30
```

## 指标解释

- `EPS`：从东财个股研报里的 `predictThisYearEps` 聚合而来，默认只取最新 20 篇，用中位数降低单篇研报极端值影响。
- `次年EPS`：从 `predictNextYearEps` 聚合而来。
- `前向PE`：当前价格 / 今年预测 EPS。
- `增速%`：次年 EPS / 今年 EPS - 1。
- `PEG`：前向 PE / 增速百分数。成长股里可作为粗筛，不适合没有增长或强周期标的。
- `消化年`：假设 EPS 按当前预测增速增长，前向 PE 回落到 30 倍需要的年数。
- `研报数`：参与 EPS 聚合的东财研报数量，不是接口返回的全部研报数量。

## 开发验证

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

联网 smoke test：

```bash
PYTHONPATH=src python -m astockdata.cli 600519 688017 --report-pages 1
```

## 缠论交易信号 V1

缠论模块是独立入口，输出 `买入 / 卖出 / 继续持有`，同时保留内部信号、买卖点、市场环境、辅助确认、信号力度、缠论结构摘要、原因、失效条件和近似复盘摘要。

单票技术信号：

```bash
PYTHONPATH=src python -m astockdata.chan_cli 688017
```

也可以直接输入股票名称：

```bash
PYTHONPATH=src python -m astockdata.chan_cli 意华股份
```

单票可选结合持仓：

```bash
PYTHONPATH=src python -m astockdata.chan_cli 688017 --cost 120.5 --position 0.3
```

JSON 输出：

```bash
PYTHONPATH=src python -m astockdata.chan_cli 688017 --json
```

CSV 批量扫描：

```csv
code
688017
意华股份
600519
```

```bash
PYTHONPATH=src python -m astockdata.chan_cli --portfolio portfolio.csv
```

历史信号验证：

```bash
PYTHONPATH=src python -m astockdata.chan_cli --backtest 600519 --horizons 5,10,20 --lookback 260
```

`--backtest` 支持股票代码或股票名称。回测会逐日回放历史 K 线，只使用当日及以前的数据生成信号，再统计未来 5 / 10 / 20 个交易日是否有利。第一版用于验证信号质量，不模拟资金曲线、手续费、滑点，也不纳入历史市场环境。

股票列表 CSV 格式说明：

- `code`：股票代码或股票名称，支持 `600519`、`sh600519`、`sz000001`、`意华股份` 这类写法。
- 第一行必须是表头：`code`。
- 每行一个股票代码或名称，用来批量扫描走势和信号。
- CLI 仍兼容可选的 `cost,position` 两列，但 Web UI 默认不需要它们。
- 文件建议保存为 UTF-8 编码。

可以直接复制示例文件再修改：

```bash
cp examples/holdings.sample.csv portfolio.csv
```

本地 Web UI：

```bash
PYTHONPATH=src python -m astockdata.web --port 8010
```

打开：

```text
http://127.0.0.1:8010
```

说明：

- 日线 K 线使用 HTTP 数据源。
- 30 分钟确认使用可选 mootdx；不可用时不会中断，会标记 `confirmation_missing` 并降低信号力度。
- “买卖点”是基于当前分型、笔、趋势和简化背驰识别出的实用近似：`一买 / 二买 / 三买 / 一卖 / 二卖 / 三卖 / 无明确买卖点`。
- “市场环境”会结合沪深300涨跌和个股所属行业板块涨跌，给出 `顺风 / 中性 / 逆风`。买入信号遇到逆风会降低信号力度并增加风险提示；顺风会小幅增强买入信号解释。
- “辅助确认”会根据 20 日均线、最近 5 个交易日涨跌幅和布林带宽度，给出 `助力 / 蓄势 / 中性 / 拖累`。它不是独立买卖依据，只用来判断当前买卖点是否有短线走势配合，或是否处在波动收窄后的等待方向阶段。
- “布林带宽”可以理解为最近 20 日价格上下波动空间。数值越小，代表价格越挤越窄，常见于蓄势；数值越大，代表波动明显放大，上涨时可能延续，但追涨也更容易遇到回撤。
- “复盘摘要”会在最近一段历史 K 线中滚动回放同类买卖点，统计后续若干日的有利走势次数、占比和平均幅度，用来帮助判断当前信号不是孤立出现。
- 页面里的“信号力度”是更通俗的展示：`偏弱 / 一般 / 较强`。JSON 里仍保留 `confidence` 原始分，供程序排序、筛选或后续回测使用。
- Web UI 的结构摘要会显示日线趋势、最新价、分型数量、笔数量、最近顶/底分型、最近一笔和背驰提示，并用白话解释背驰含义。
- Web UI 会绘制最近日线 K 线走势，方便快速看走势形态。
- CSV 批量结果会展示每只股票的动作、内部信号、买卖点、市场环境、辅助确认、信号力度和 30 分钟确认状态，点击表格行可以切换查看单只股票详情。
- 当前买卖点仍是实用近似缠论结构，不等同完整标准线段/中枢算法；后续会继续补标准中枢和更严格的三类买卖点。
- 所有信号只作为辅助决策，不构成投资建议。
