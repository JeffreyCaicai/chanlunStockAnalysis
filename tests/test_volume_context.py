import unittest

from astockdata.kline import KLine
from astockdata.volume_context import build_volume_context


def kline(index, close, volume=100.0, amount=None):
    return KLine(
        "600519",
        "1d",
        f"2026-06-{index:02d}",
        close,
        close + 1,
        close - 1,
        close,
        float(volume),
        float(amount if amount is not None else volume * close),
    )


def base_rows():
    return [kline(index, 10 + index * 0.1, 100.0, 1000.0) for index in range(1, 22)]


class VolumeContextTests(unittest.TestCase):
    def test_volume_surge_up_supports_buy_confirmation(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 21.0, 160.0, 1800.0)

        context = build_volume_context(rows, turnover_pct=6.2)

        self.assertEqual(context.label, "助力")
        self.assertEqual(context.volume_label, "放量上涨")
        self.assertGreater(context.volume_ratio_5, 1.3)
        self.assertEqual(context.turnover_label, "换手活跃")
        self.assertIn("放量上涨", context.summary)

    def test_shrinking_volume_pullback_is_setup(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 19.0, 70.0, 700.0)

        context = build_volume_context(rows)

        self.assertEqual(context.label, "蓄势")
        self.assertEqual(context.volume_label, "缩量回调")
        self.assertIn("抛压不强", context.summary)

    def test_volume_surge_down_flags_risk(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 18.5, 170.0, 1800.0)

        context = build_volume_context(rows)

        self.assertEqual(context.label, "拖累")
        self.assertEqual(context.volume_label, "放量下跌")
        self.assertIn("放量下跌", context.risk_notes)

    def test_low_volume_rise_is_weak(self):
        rows = base_rows()
        rows[-2] = kline(21, 20.0, 100.0, 1000.0)
        rows[-1] = kline(22, 21.0, 70.0, 760.0)

        context = build_volume_context(rows)

        self.assertEqual(context.label, "拖累")
        self.assertEqual(context.volume_label, "无量上涨")
        self.assertIn("成交量没有跟上", context.summary)

    def test_insufficient_rows_returns_neutral_context(self):
        context = build_volume_context(base_rows()[:10])

        self.assertEqual(context.label, "中性")
        self.assertEqual(context.volume_label, "数据不足")
        self.assertIn("量能数据不足", context.summary)
