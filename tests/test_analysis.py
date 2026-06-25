import unittest

from astockdata.analysis import Analyzer, aggregate_eps, calc_peg, pe_digest_years, recent_reports
from astockdata.models import Quote, ResearchReport, StockInfo


class FakeMarketData:
    def __init__(self):
        self.quote = Quote(
            code="688017",
            name="绿的谐波",
            price=391.0,
            last_close=390.0,
            open=391.0,
            change_amount=1.0,
            change_pct=0.25,
            high=400.0,
            low=380.0,
            amount_wan=10000.0,
            turnover_pct=2.0,
            pe_ttm=524.17,
            amplitude_pct=5.0,
            market_cap_yi=716.82,
            float_market_cap_yi=716.82,
            pb=20.09,
            limit_up=430.0,
            limit_down=352.0,
            volume_ratio=1.1,
            pe_static=500.0,
        )
        self.info = StockInfo(
            code="688017",
            name="绿的谐波",
            industry="自动化设备",
            total_shares=183253582,
            float_shares=183253582,
            market_cap=71682000000,
            float_market_cap=71682000000,
            list_date="20200828",
            price=391.0,
        )
        self.reports = [
            ResearchReport("A", "2026-05-26", "国信证券", "报告一", "增持", 1.03, 1.36, None),
            ResearchReport("B", "2026-04-29", "国元证券", "报告二", "增持", 1.07, 1.40, None),
            ResearchReport("C", "2026-04-23", "群益证券", "报告三", "增持", 0.94, 1.38, None),
        ]

    def quotes(self, codes):
        return {code: self.quote for code in codes}

    def stock_info(self, code):
        return self.info

    def reports_for(self, code, max_pages=1):
        return self.reports


class AnalysisTests(unittest.TestCase):
    def test_aggregate_eps_uses_median_to_reduce_single_report_noise(self):
        estimate = aggregate_eps(
            [
                ResearchReport("A", "2026-01-01", "A", "a", "", 1.0, 1.4, None),
                ResearchReport("B", "2026-01-02", "B", "b", "", 1.1, 1.5, None),
                ResearchReport("C", "2026-01-03", "C", "c", "", 9.9, 9.9, None),
            ]
        )

        self.assertEqual(estimate.report_count, 3)
        self.assertEqual(estimate.eps_this_year, 1.1)
        self.assertEqual(estimate.eps_next_year, 1.5)

    def test_recent_reports_sorts_descending_and_limits_count(self):
        reports = [
            ResearchReport("old", "2025-01-01", "A", "old", "", 0.5, 0.6, None),
            ResearchReport("new", "2026-05-01", "B", "new", "", 1.0, 1.2, None),
            ResearchReport("mid", "2026-01-01", "C", "mid", "", 0.8, 1.0, None),
        ]

        selected = recent_reports(reports, limit=2)

        self.assertEqual([report.info_code for report in selected], ["new", "mid"])

    def test_valuation_math_handles_growth_and_non_growth_cases(self):
        self.assertAlmostEqual(calc_peg(30.0, 0.30), 1.0)
        self.assertEqual(calc_peg(30.0, 0.0), None)
        self.assertAlmostEqual(pe_digest_years(60.0, 0.30, target_pe=30.0), 2.64, places=2)
        self.assertEqual(pe_digest_years(20.0, 0.30, target_pe=30.0), 0.0)
        self.assertEqual(pe_digest_years(60.0, 0.0, target_pe=30.0), None)

    def test_analyze_stock_combines_quote_info_and_reports(self):
        market_data = FakeMarketData()
        analyzer = Analyzer(market_data, max_reports=2)

        result = analyzer.analyze_stock("688017")

        self.assertEqual(result.code, "688017")
        self.assertEqual(result.name, "绿的谐波")
        self.assertEqual(result.industry, "自动化设备")
        self.assertEqual(result.eps_report_count, 2)
        self.assertEqual(result.eps_this_year, 1.05)
        self.assertEqual(result.eps_next_year, 1.38)
        self.assertAlmostEqual(result.forward_pe, 372.38, places=2)
        self.assertAlmostEqual(result.growth_pct, 31.43, places=2)
        self.assertAlmostEqual(result.peg, 11.85, places=2)


if __name__ == "__main__":
    unittest.main()
