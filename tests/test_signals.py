import unittest

from astockdata.chan import ChanStructure, Fractal, Stroke
from astockdata.kline import KLine
from astockdata.signals import ChanSignalEngine, Position, map_signal_to_action


def kline(ts, open_, high, low, close):
    return KLine("600519", "1d", ts, open_, high, low, close, 100.0, 1000.0)


class SignalTests(unittest.TestCase):
    def make_structure(self, trend="uptrend", up_risk=False):
        bottom = Fractal("bottom", "1", 10.0, 0)
        top = Fractal("top", "2", 15.0, 4)
        return ChanStructure(
            merged=[],
            fractals=[bottom, top],
            strokes=[Stroke(bottom, top, "up", 5.0, 100.0)],
            trend=trend,
            up_divergence_risk=up_risk,
            down_divergence_repair=False,
        )

    def test_map_internal_signals_to_external_actions(self):
        self.assertEqual(map_signal_to_action("强买入"), "买入")
        self.assertEqual(map_signal_to_action("试买入"), "买入")
        self.assertEqual(map_signal_to_action("观察"), "继续持有")
        self.assertEqual(map_signal_to_action("减仓"), "卖出")
        self.assertEqual(map_signal_to_action("清仓卖出"), "卖出")

    def test_missing_30m_confirmation_degrades_buy_signal(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.make_structure("uptrend"),
            confirm_structure=None,
            latest_price=12.0,
        )

        self.assertEqual(signal.signal, "试买入")
        self.assertEqual(signal.action, "买入")
        self.assertTrue(signal.confirmation_missing)
        self.assertLess(signal.confidence, 0.7)

    def test_signal_includes_plain_strength_and_structure_summary(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.make_structure("uptrend"),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=12.0,
        )

        payload = signal.to_dict()
        self.assertEqual(payload["strength_label"], "较强")
        self.assertEqual(payload["confirmation_status"], "有效确认")
        self.assertEqual(payload["daily_summary"]["trend_label"], "上升趋势")
        self.assertEqual(payload["daily_summary"]["stroke_count"], 1)
        self.assertEqual(payload["daily_summary"]["latest_bottom"]["price"], 10.0)
        self.assertEqual(payload["confirmation_summary"]["trend_label"], "上升趋势")

    def test_signal_includes_recent_daily_klines_for_chart(self):
        engine = ChanSignalEngine()
        rows = [
            kline("2026-06-23", 10, 12, 9, 11),
            kline("2026-06-24", 11, 13, 10, 12),
            kline("2026-06-25", 12, 12.5, 10.5, 11),
        ]

        signal = engine.evaluate(
            "600519",
            daily_structure=self.make_structure("range"),
            confirm_structure=None,
            latest_price=11.0,
            recent_klines=rows,
        )

        payload = signal.to_dict()
        self.assertEqual(len(payload["recent_klines"]), 3)
        self.assertEqual(payload["recent_klines"][-1]["timestamp"], "2026-06-25")
        self.assertEqual(payload["recent_klines"][-1]["close"], 11.0)

    def test_confirmation_status_marks_weak_30m_structure(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.make_structure("uptrend"),
            confirm_structure=self.make_structure("unknown"),
            latest_price=12.0,
        )

        self.assertEqual(signal.confirmation_status, "结构不足")

    def test_position_turns_broken_structure_into_sell_signal(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.make_structure("downtrend"),
            confirm_structure=self.make_structure("downtrend"),
            latest_price=9.0,
            position=Position(cost=10.0, position=0.5),
        )

        self.assertEqual(signal.action, "卖出")
        self.assertEqual(signal.signal, "清仓卖出")
        self.assertIn("跌破持仓成本", signal.risk_notes[0])

    def test_signal_to_dict_is_json_safe(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.make_structure("range"),
            confirm_structure=None,
            latest_price=12.0,
            intraday=True,
        )

        payload = signal.to_dict()
        self.assertEqual(payload["code"], "600519")
        self.assertTrue(payload["intraday"])
        self.assertFalse(payload["confirmed"])
        self.assertIn("reasons", payload)


if __name__ == "__main__":
    unittest.main()
