import json
import unittest

from astockdata.signals import ChanSignal
from astockdata.web import handle_api_request


class FakeAnalyzer:
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
        self.assertIn("背驰说明", body)
        self.assertIn("CSV 示例", body)
        self.assertIn('id="portfolioTable"', body)
        self.assertIn('id="klineChart"', body)
        self.assertIn('id="divergenceHelp"', body)
        self.assertIn("复制失败", body)
        self.assertNotIn("持仓成本", body)
        self.assertNotIn("仓位比例", body)
        self.assertIn("/api/analyze-portfolio", body)


if __name__ == "__main__":
    unittest.main()
