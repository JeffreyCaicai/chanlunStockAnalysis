import json
import unittest

from astockdata.kline import KLine
from astockdata.resolver import StockIdentity
from astockdata.signals import ChanSignal
from astockdata.web import handle_api_request


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


class FakeEmptyDailyKLineProvider:
    def daily_klines(self, code):
        return []

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


class FakeEmptyDailyAnalyzer(FakeAnalyzer):
    def __init__(self):
        super().__init__()
        self.kline_provider = FakeEmptyDailyKLineProvider()


class WebTests(unittest.TestCase):
    def test_health_endpoint(self):
        status, headers, body = handle_api_request("GET", "/api/health", b"", FakeAnalyzer())

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body)["status"], "ok")

    def test_analyze_endpoint_returns_signal(self):
        payload = json.dumps({"code": "意华股份", "intraday": True}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/analyze", payload, FakeAnalyzer())

        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["code"], "002897")
        self.assertEqual(data["stock_name"], "意华股份")
        self.assertFalse(data["confirmed"])

    def test_analyze_requires_code(self):
        payload = json.dumps({"intraday": False}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/analyze", payload, FakeAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("code is required", json.loads(body)["error"])

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

    def test_backtest_endpoint_rejects_empty_horizons(self):
        payload = json.dumps({"code": "600519", "horizons": []}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("horizons must be positive integers", json.loads(body)["error"])

    def test_backtest_endpoint_rejects_malformed_horizon_values(self):
        for value in (1.9, "2", True):
            with self.subTest(value=value):
                payload = json.dumps({"code": "600519", "horizons": [value]}).encode("utf-8")

                status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

                self.assertEqual(status, 400)
                self.assertIn("horizons must be positive integers", json.loads(body)["error"])

    def test_backtest_endpoint_validates_horizons_before_daily_klines(self):
        payload = json.dumps({"code": "600519", "horizons": [1.9]}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeEmptyDailyAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("horizons must be positive integers", json.loads(body)["error"])

    def test_backtest_endpoint_rejects_zero_min_history(self):
        payload = json.dumps({"code": "600519", "min_history": 0}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("min_history must be positive", json.loads(body)["error"])

    def test_backtest_endpoint_rejects_malformed_min_history_values(self):
        for value in (1.9, "2", True):
            with self.subTest(value=value):
                payload = json.dumps({"code": "600519", "min_history": value}).encode("utf-8")

                status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

                self.assertEqual(status, 400)
                self.assertIn("min_history must be positive", json.loads(body)["error"])

    def test_backtest_endpoint_validates_min_history_before_daily_klines(self):
        payload = json.dumps({"code": "600519", "min_history": 1.9}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeEmptyDailyAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("min_history must be positive", json.loads(body)["error"])

    def test_backtest_endpoint_rejects_non_object_payload(self):
        for payload_value in ([], None):
            with self.subTest(payload=payload_value):
                payload = json.dumps(payload_value).encode("utf-8")

                status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeAnalyzer())

                self.assertEqual(status, 400)
                self.assertIn("payload must be a JSON object", json.loads(body)["error"])

    def test_backtest_endpoint_rejects_empty_daily_klines(self):
        payload = json.dumps({"code": "600519", "horizons": [2], "min_history": 5}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/backtest", payload, FakeEmptyDailyAnalyzer())

        self.assertEqual(status, 400)
        self.assertIn("No daily K-line data returned", json.loads(body)["error"])

    def test_portfolio_endpoint_returns_results(self):
        payload = json.dumps({"holdings": [{"code": "600519", "cost": 1000, "position": 0.2}]}).encode("utf-8")

        status, _headers, body = handle_api_request("POST", "/api/analyze-portfolio", payload, FakeAnalyzer())

        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(data["results"][0]["position_context"]["position"], 0.2)

    def test_root_serves_html(self):
        status, headers, body = handle_api_request("GET", "/", b"", FakeAnalyzer())

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("股票交易信号", body)
        self.assertNotIn("缠论交易信号", body)
        self.assertIn('class="workbench"', body)
        self.assertIn("股票代码或名称", body)
        self.assertIn('id="stockIdentity"', body)
        self.assertIn("<span>股票</span>", body)
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
        self.assertIn('id="csvFile"', body)
        self.assertIn("信号力度", body)
        self.assertIn('id="strengthHint"', body)
        self.assertIn("strengthExplanation", body)
        self.assertIn("市场环境", body)
        self.assertIn('id="marketContext"', body)
        self.assertIn('id="marketContextDetail"', body)
        self.assertIn("辅助确认", body)
        self.assertIn('id="technicalContext"', body)
        self.assertIn('id="technicalContextDetail"', body)
        self.assertIn("量能换手", body)
        self.assertIn('id="volumeContext"', body)
        self.assertIn('id="volumeContextDetail"', body)
        self.assertIn("volumeContextText", body)
        self.assertIn("否决条件", body)
        self.assertIn('id="vetoStatus"', body)
        self.assertIn('id="vetoDetail"', body)
        self.assertIn("vetoContextText", body)
        self.assertIn('id="filterAction"', body)
        self.assertIn('id="filterVeto"', body)
        self.assertIn('id="filterVolume"', body)
        self.assertIn("filterPortfolioResults", body)
        self.assertIn("setActivePortfolioRow", body)
        self.assertIn('id="riskNotes"', body)
        self.assertIn('class="explain-grid"', body)
        self.assertIn("没有符合筛选条件的股票", body)
        self.assertIn("结构摘要", body)
        self.assertIn("买卖点", body)
        self.assertIn('id="tradePoint"', body)
        self.assertIn('id="tradePointReplay"', body)
        self.assertIn("最近K线走势", body)
        self.assertIn('<button id="backtestButton" class="secondary" onclick="runBacktest()">运行复盘</button>', body)
        self.assertIn('id="backtestState"', body)
        self.assertIn("信号复盘", body)
        self.assertIn("复盘总览", body)
        self.assertIn('id="backtestOverview"', body)
        self.assertIn('class="backtest-overview"', body)
        self.assertIn("周期表现", body)
        self.assertIn('id="backtestHorizonRows"', body)
        self.assertIn("分层验证", body)
        self.assertIn('class="backtest-grid"', body)
        self.assertIn(".backtest-grid > div {\n      min-width: 0;\n    }", body)
        self.assertIn('class="backtest-table-title"', body)
        self.assertIn('id="backtestActionRows"', body)
        self.assertIn('id="backtestTradePointRows"', body)
        self.assertIn('id="backtestStrengthRows"', body)
        self.assertIn('id="backtestTechnicalRows"', body)
        self.assertIn("最近信号样本", body)
        self.assertIn('id="backtestSampleRows"', body)
        self.assertIn("背驰说明", body)
        self.assertIn("CSV 示例", body)
        self.assertIn('id="portfolioTable"', body)
        self.assertIn('id="klineChart"', body)
        self.assertIn('id="chartLegend"', body)
        self.assertIn("invalidPrice", body)
        self.assertIn("drawPriceLine", body)
        self.assertIn("drawMarker", body)
        self.assertIn("中枢上沿", body)
        self.assertIn("失效价", body)
        self.assertIn('id="divergenceHelp"', body)
        self.assertIn("复制失败", body)
        self.assertNotIn("持仓成本", body)
        self.assertNotIn("仓位比例", body)
        self.assertIn("/api/analyze-portfolio", body)


if __name__ == "__main__":
    unittest.main()
