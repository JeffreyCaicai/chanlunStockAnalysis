import unittest

from astockdata.market_context import (
    BoardSnapshot,
    IndexSnapshot,
    MarketContext,
    build_market_context,
    match_sector,
)


class MarketContextTests(unittest.TestCase):
    def test_supportive_market_and_sector_scores_as_tailwind(self):
        context = build_market_context(
            index=IndexSnapshot("000300", "沪深300", 1.2),
            industry="电子元件",
            sector=BoardSnapshot("BK0001", "电子元件", 2.4, 3.1),
        )

        self.assertEqual(context.label, "顺风")
        self.assertGreaterEqual(context.score, 0.65)
        self.assertIn("沪深300上涨1.20%", context.summary)
        self.assertIn("电子元件上涨2.40%", context.summary)

    def test_weak_market_and_sector_scores_as_headwind(self):
        context = build_market_context(
            index=IndexSnapshot("000300", "沪深300", -1.4),
            industry="电子元件",
            sector=BoardSnapshot("BK0001", "电子元件", -2.0, 4.5),
        )

        self.assertEqual(context.label, "逆风")
        self.assertLessEqual(context.score, 0.4)
        self.assertIn("大盘和板块都偏弱", context.risk_notes)

    def test_sector_matching_accepts_partial_industry_name(self):
        sector = match_sector(
            "消费电子",
            [
                BoardSnapshot("BK0001", "半导体", 0.5, 2.0),
                BoardSnapshot("BK0002", "电子", 1.1, 3.0),
            ],
        )

        self.assertEqual(sector.code, "BK0002")

    def test_missing_sector_keeps_neutral_context_readable(self):
        context = build_market_context(
            index=IndexSnapshot("000300", "沪深300", 0.1),
            industry="自动化设备",
            sector=None,
        )

        self.assertEqual(context.label, "中性")
        self.assertEqual(context.industry, "自动化设备")
        self.assertIn("暂未匹配到行业板块", context.summary)
        self.assertIsInstance(context, MarketContext)


if __name__ == "__main__":
    unittest.main()
