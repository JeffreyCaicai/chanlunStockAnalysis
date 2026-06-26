import unittest

from astockdata.chan import ChanStructure, Fractal, Stroke
from astockdata.chan_points import (
    TradePointReplaySample,
    classify_trade_point,
    replay_trade_points,
    summarize_replay_samples,
)
from astockdata.kline import KLine


def fractal(kind, ts, price, index):
    return Fractal(kind, ts, float(price), index)


def stroke(start, end):
    direction = "up" if start.kind == "bottom" and end.kind == "top" else "down"
    return Stroke(start, end, direction, abs(end.price - start.price), 100.0)


def structure(strokes, trend="range", up_risk=False, down_repair=False):
    fractals = []
    for item in strokes:
        if item.start not in fractals:
            fractals.append(item.start)
        if item.end not in fractals:
            fractals.append(item.end)
    return ChanStructure(
        merged=[],
        fractals=fractals,
        strokes=strokes,
        trend=trend,
        up_divergence_risk=up_risk,
        down_divergence_repair=down_repair,
    )


def kline(ts, open_, high, low, close):
    return KLine("600519", "1d", str(ts), open_, high, low, close, 100.0, 1000.0)


class ChanTradePointTests(unittest.TestCase):
    def test_first_buy_uses_down_divergence_repair(self):
        top1 = fractal("top", "1", 20, 1)
        bottom1 = fractal("bottom", "2", 10, 5)
        top2 = fractal("top", "3", 16, 9)
        bottom2 = fractal("bottom", "4", 8, 13)
        point = classify_trade_point(
            structure(
                [stroke(top1, bottom1), stroke(bottom1, top2), stroke(top2, bottom2)],
                trend="downtrend",
                down_repair=True,
            ),
            latest_price=8.8,
        )

        self.assertEqual(point.kind, "first_buy")
        self.assertEqual(point.label, "一买")
        self.assertEqual(point.action_bias, "buy")
        self.assertEqual(point.timestamp, "4")
        self.assertEqual(point.price, 8.0)
        self.assertIn("下跌力度衰竭", point.explanation)
        self.assertIn("8.00", point.invalidation)

    def test_second_buy_when_pullback_holds_above_prior_bottom(self):
        top1 = fractal("top", "1", 18, 1)
        bottom1 = fractal("bottom", "2", 10, 5)
        top2 = fractal("top", "3", 15, 9)
        bottom2 = fractal("bottom", "4", 12, 13)
        point = classify_trade_point(
            structure([stroke(top1, bottom1), stroke(bottom1, top2), stroke(top2, bottom2)]),
            latest_price=12.8,
        )

        self.assertEqual(point.kind, "second_buy")
        self.assertEqual(point.label, "二买")
        self.assertIn("回调不破前低", point.explanation)

    def test_first_sell_uses_up_divergence_risk(self):
        bottom1 = fractal("bottom", "1", 10, 1)
        top1 = fractal("top", "2", 18, 5)
        bottom2 = fractal("bottom", "3", 14, 9)
        top2 = fractal("top", "4", 19, 13)
        point = classify_trade_point(
            structure(
                [stroke(bottom1, top1), stroke(top1, bottom2), stroke(bottom2, top2)],
                trend="uptrend",
                up_risk=True,
            ),
            latest_price=18.5,
        )

        self.assertEqual(point.kind, "first_sell")
        self.assertEqual(point.label, "一卖")
        self.assertEqual(point.action_bias, "sell")
        self.assertIn("上涨力度衰竭", point.explanation)

    def test_replay_summary_counts_favorable_follow_through(self):
        replay = summarize_replay_samples(
            "second_buy",
            "二买",
            "buy",
            horizon_days=5,
            samples=[
                TradePointReplaySample("2026-06-01", 10.0, 11.0),
                TradePointReplaySample("2026-06-05", 20.0, 18.0),
                TradePointReplaySample("2026-06-10", 30.0, 33.0),
            ],
        )

        self.assertEqual(replay.sample_count, 3)
        self.assertEqual(replay.favorable_count, 2)
        self.assertEqual(replay.favorable_rate, 0.67)
        self.assertEqual(replay.average_return_pct, 3.33)
        self.assertIn("近3次二买", replay.summary)

    def test_replay_trade_points_scans_historical_klines(self):
        rows = [
            kline(1, 10, 11, 9, 10),
            kline(2, 10, 18, 12, 17),
            kline(3, 17, 15, 11, 12),
            kline(4, 12, 13, 10, 11),
            kline(5, 11, 14, 11, 13),
            kline(6, 13, 15, 13, 14),
            kline(7, 14, 14, 13, 13.5),
            kline(8, 13.5, 13, 12, 12.5),
            kline(9, 12.5, 14, 13, 13.8),
            kline(10, 13.8, 15, 13.5, 14.8),
            kline(11, 14.8, 16, 14, 15.5),
        ]

        replay = replay_trade_points(
            rows,
            kind="first_buy",
            label="一买",
            action_bias="buy",
            horizon_days=2,
            min_gap=1,
        )

        self.assertGreaterEqual(replay.sample_count, 1)
        self.assertGreater(replay.average_return_pct, 0)
        self.assertIn("一买", replay.summary)


if __name__ == "__main__":
    unittest.main()
