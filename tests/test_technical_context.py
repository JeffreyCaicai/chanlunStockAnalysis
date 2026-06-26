import unittest

from astockdata.kline import KLine
from astockdata.technical_context import build_technical_context


def kline(index, close):
    return KLine(
        "600519",
        "1d",
        f"2026-05-{index:02d}",
        close - 0.2,
        close + 0.8,
        close - 0.8,
        close,
        100.0,
        1000.0,
    )


class TechnicalContextTests(unittest.TestCase):
    def test_upward_momentum_supports_buy_confirmation(self):
        rows = [kline(index + 1, 80 + index * 0.8) for index in range(45)]

        context = build_technical_context(rows)

        self.assertEqual(context.label, "助力")
        self.assertEqual(context.momentum_label, "动量向上")
        self.assertGreater(context.score, 0.55)
        self.assertIn("5日涨幅", context.summary)

    def test_downward_momentum_flags_buy_risk(self):
        rows = [kline(index + 1, 120 - index * 0.9) for index in range(45)]

        context = build_technical_context(rows)

        self.assertEqual(context.label, "拖累")
        self.assertEqual(context.momentum_label, "动量走弱")
        self.assertIn("趋势动量走弱", context.risk_notes)

    def test_bollinger_compression_is_reported_as_setup(self):
        rows = []
        for index in range(45):
            close = 100 + (8 if index % 2 == 0 else -8)
            rows.append(kline(index + 1, close))
        for index in range(35):
            close = 100 + (0.25 if index % 2 == 0 else -0.25)
            rows.append(kline(index + 46, close))

        context = build_technical_context(rows)

        self.assertIn(context.bollinger_label, {"布林压缩", "压缩后向上突破", "压缩后向下突破"})
        self.assertIn("布林", context.summary)
        self.assertIn("等待方向选择", context.reasons)

    def test_insufficient_rows_returns_neutral_readable_context(self):
        context = build_technical_context([kline(1, 100), kline(2, 101)])

        self.assertEqual(context.label, "中性")
        self.assertEqual(context.momentum_label, "数据不足")
        self.assertIn("技术辅助数据不足", context.summary)


if __name__ == "__main__":
    unittest.main()
