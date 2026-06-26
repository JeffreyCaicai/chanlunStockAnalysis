import unittest

from astockdata.backtest import BacktestSample, build_outcome_sample, run_signal_backtest, summarize_samples
from astockdata.kline import KLine
from astockdata.signals import ChanSignal


def kline(timestamp, close, high=None, low=None):
    return KLine("600519", "1d", timestamp, close, high or close, low or close, close, 100.0, 1000.0)


def signal(action):
    return ChanSignal(
        code="600519",
        action=action,
        signal="强买入" if action == "买入" else "减仓",
        confidence=0.78,
        strength_label="较强",
        confirmed=True,
        intraday=False,
        confirmation_missing=True,
        reasons=[],
        invalidations=[],
        risk_notes=[],
        trade_point=None,
        technical_context=None,
    )


class FakeEngine:
    def __init__(self):
        self.seen_latest_timestamps = []

    def evaluate(self, **kwargs):
        rows = kwargs["recent_klines"]
        self.seen_latest_timestamps.append(rows[-1].timestamp)
        action = "买入" if rows[-1].close >= rows[-2].close else "卖出"
        return ChanSignal(
            code=kwargs["code"],
            action=action,
            signal="强买入" if action == "买入" else "减仓",
            confidence=0.78,
            strength_label="较强",
            confirmed=True,
            intraday=False,
            confirmation_missing=True,
            reasons=[],
            invalidations=[],
            risk_notes=[],
            trade_point=None,
            technical_context=kwargs["technical_context"],
        )


class BacktestTests(unittest.TestCase):
    def test_summarize_samples_calculates_rates_and_averages(self):
        samples = [
            BacktestSample(
                code="600519",
                timestamp="2026-01-01",
                action="买入",
                signal="强买入",
                confidence=0.8,
                strength_label="较强",
                trade_point_label="一买",
                technical_label="助力",
                entry_price=10.0,
                horizon_days=5,
                exit_price=11.0,
                return_pct=10.0,
                favorable=True,
                max_favorable_pct=15.0,
                max_adverse_pct=-2.0,
            ),
            BacktestSample(
                code="600519",
                timestamp="2026-01-02",
                action="买入",
                signal="试买入",
                confidence=0.62,
                strength_label="一般",
                trade_point_label="二买",
                technical_label="拖累",
                entry_price=10.0,
                horizon_days=5,
                exit_price=9.0,
                return_pct=-10.0,
                favorable=False,
                max_favorable_pct=3.0,
                max_adverse_pct=-12.0,
            ),
        ]

        summary = summarize_samples("5日", samples)

        self.assertEqual(summary.name, "5日")
        self.assertEqual(summary.sample_count, 2)
        self.assertEqual(summary.favorable_count, 1)
        self.assertEqual(summary.favorable_rate, 0.5)
        self.assertEqual(summary.average_return_pct, 0.0)
        self.assertEqual(summary.average_max_favorable_pct, 9.0)
        self.assertEqual(summary.average_max_adverse_pct, -7.0)
        self.assertEqual(summary.best_return_pct, 10.0)
        self.assertEqual(summary.worst_return_pct, -10.0)

    def test_summarize_samples_returns_empty_summary(self):
        summary = summarize_samples("empty", [])

        self.assertEqual(summary.sample_count, 0)
        self.assertIsNone(summary.favorable_rate)
        self.assertIsNone(summary.average_return_pct)

    def test_buy_outcome_uses_forward_return_and_drawdown(self):
        entry = kline("2026-01-01", 10.0)
        future = [
            kline("2026-01-02", 10.5, high=11.0, low=9.8),
            kline("2026-01-03", 11.0, high=11.5, low=10.2),
        ]

        sample = build_outcome_sample("600519", signal("买入"), entry, future, 2)

        self.assertTrue(sample.favorable)
        self.assertEqual(sample.return_pct, 10.0)
        self.assertEqual(sample.max_favorable_pct, 15.0)
        self.assertEqual(sample.max_adverse_pct, -2.0)

    def test_buy_outcome_clamps_adverse_to_zero_when_price_never_breaks_entry(self):
        entry = kline("2026-01-01", 10.0)
        future = [
            kline("2026-01-02", 10.5, high=10.8, low=10.2),
            kline("2026-01-03", 11.0, high=11.5, low=10.4),
        ]

        sample = build_outcome_sample("600519", signal("买入"), entry, future, 2)

        self.assertEqual(sample.max_favorable_pct, 15.0)
        self.assertEqual(sample.max_adverse_pct, 0.0)

    def test_sell_outcome_uses_inverse_return_and_adverse_rally(self):
        entry = kline("2026-01-01", 10.0)
        future = [
            kline("2026-01-02", 9.5, high=10.4, low=9.0),
            kline("2026-01-03", 9.0, high=9.8, low=8.8),
        ]

        sample = build_outcome_sample("600519", signal("卖出"), entry, future, 2)

        self.assertTrue(sample.favorable)
        self.assertEqual(sample.return_pct, 10.0)
        self.assertEqual(sample.max_favorable_pct, 12.0)
        self.assertEqual(sample.max_adverse_pct, -4.0)

    def test_sell_outcome_clamps_adverse_to_zero_when_price_never_rallies_above_entry(self):
        entry = kline("2026-01-01", 10.0)
        future = [
            kline("2026-01-02", 9.5, high=9.8, low=9.0),
            kline("2026-01-03", 9.0, high=9.6, low=8.8),
        ]

        sample = build_outcome_sample("600519", signal("卖出"), entry, future, 2)

        self.assertEqual(sample.max_favorable_pct, 12.0)
        self.assertEqual(sample.max_adverse_pct, 0.0)

    def test_run_signal_backtest_rolls_without_future_leakage(self):
        rows = [kline(f"2026-01-{index + 1:02d}", 10 + index * 0.1) for index in range(12)]
        engine = FakeEngine()

        report = run_signal_backtest("600519", rows, horizons=[2], min_history=5, engine=engine)

        self.assertEqual(report.code, "600519")
        self.assertGreater(report.sample_count, 0)
        self.assertNotIn("2026-01-12", engine.seen_latest_timestamps)
        self.assertEqual(report.by_horizon[0].name, "2日")
        self.assertEqual(report.by_action[0].name, "买入")

    def test_run_signal_backtest_preserves_horizon_order(self):
        rows = [kline(f"2026-01-{index + 1:02d}", 10 + index * 0.1) for index in range(40)]
        engine = FakeEngine()

        report = run_signal_backtest("600519", rows, horizons=[5, 10, 20], min_history=5, engine=engine)

        self.assertEqual([item.name for item in report.by_horizon], ["5日", "10日", "20日"])

    def test_run_signal_backtest_returns_empty_report_when_rows_are_insufficient(self):
        report = run_signal_backtest("600519", [kline("2026-01-01", 10.0)], horizons=[5], min_history=5)

        self.assertEqual(report.sample_count, 0)
        self.assertIn("样本不足", report.summary)


if __name__ == "__main__":
    unittest.main()
