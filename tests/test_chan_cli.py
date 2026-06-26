import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from astockdata.backtest import BacktestBucketSummary, BacktestReport, BacktestSample
from astockdata.chan_cli import (
    load_portfolio_csv,
    parse_horizons,
    render_backtest_json,
    render_backtest_table,
    render_json,
    render_table,
)
from astockdata.chan_points import TradePoint, TradePointReplay
from astockdata.market_context import MarketContext
from astockdata.signals import ChanSignal, Position
from astockdata.technical_context import TechnicalContext


class ChanCliTests(unittest.TestCase):
    def sample_signal(self):
        return ChanSignal(
            code="600519",
            action="继续持有",
            signal="持有",
            confidence=0.72,
            strength_label="较强",
            confirmed=True,
            intraday=False,
            confirmation_missing=False,
            reasons=["日线结构未破坏"],
            invalidations=["跌破 1200.00"],
            risk_notes=[],
            trade_point=TradePoint(
                kind="second_buy",
                label="二买",
                action_bias="buy",
                timestamp="2026-06-25",
                price=1000.0,
                score=0.72,
                explanation="回调不破前低，形成二买观察点。",
                invalidation="跌破二买回调低点 1000.00",
            ),
            trade_point_replay=TradePointReplay(
                kind="second_buy",
                label="二买",
                horizon_days=5,
                sample_count=3,
                favorable_count=2,
                favorable_rate=0.67,
                average_return_pct=3.33,
                best_return_pct=10.0,
                worst_return_pct=-5.0,
                summary="近3次二买后5日，有利走势2次，占比67%，平均有利幅度3.33%。",
            ),
            market_context=MarketContext(
                label="顺风",
                score=0.72,
                index=None,
                industry="电子元件",
                sector=None,
                summary="沪深300上涨1.20%；电子元件上涨2.40%",
                reasons=["沪深300上涨1.20%"],
                risk_notes=[],
            ),
            technical_context=TechnicalContext(
                label="助力",
                score=0.72,
                momentum_label="动量向上",
                momentum_score=0.7,
                ma20=1000.0,
                ma20_slope_pct=1.2,
                roc5_pct=3.5,
                bollinger_label="正常波动",
                bollinger_width_pct=8.2,
                bollinger_width_percentile=0.55,
                summary="趋势动量向上；布林正常波动",
                reasons=["趋势动量向上"],
                risk_notes=[],
            ),
            position_context=Position(cost=1000.0, position=0.2),
        )

    def sample_backtest_report(self):
        sample = BacktestSample(
            code="600519",
            timestamp="2026-01-01",
            action="买入",
            signal="强买入",
            confidence=0.78,
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
        )
        horizon = BacktestBucketSummary("5日", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)
        return BacktestReport(
            code="600519",
            start_timestamp="2026-01-01",
            end_timestamp="2026-02-01",
            horizons=[5],
            sample_count=1,
            skipped_hold_count=0,
            by_horizon=[horizon],
            by_action=[BacktestBucketSummary("买入", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            by_trade_point=[BacktestBucketSummary("一买", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            by_strength=[BacktestBucketSummary("较强", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            by_technical=[BacktestBucketSummary("助力", 1, 1, 1.0, 10.0, 15.0, -2.0, 10.0, 10.0)],
            samples=[sample],
            summary="共生成1条买卖信号回测样本，跳过0条继续持有信号。",
        )

    def test_render_json_is_machine_readable(self):
        buf = StringIO()

        render_json([self.sample_signal()], buf)

        data = json.loads(buf.getvalue())
        self.assertEqual(data[0]["signal"], "持有")
        self.assertEqual(data[0]["position_context"]["cost"], 1000.0)

    def test_render_table_contains_core_fields(self):
        buf = StringIO()

        render_table([self.sample_signal()], buf)

        output = buf.getvalue()
        self.assertIn("代码", output)
        self.assertIn("买卖点", output)
        self.assertIn("环境", output)
        self.assertIn("辅助", output)
        self.assertIn("信号力度", output)
        self.assertIn("二买", output)
        self.assertIn("顺风", output)
        self.assertIn("助力", output)
        self.assertIn("较强", output)
        self.assertIn("继续持有", output)
        self.assertIn("日线结构未破坏", output)

    def test_parse_horizons(self):
        self.assertEqual(parse_horizons("5,10,20"), [5, 10, 20])

    def test_render_backtest_table_contains_core_fields(self):
        buf = StringIO()

        render_backtest_table(self.sample_backtest_report(), buf)

        output = buf.getvalue()
        self.assertIn("回测摘要", output)
        self.assertIn("有利率", output)
        self.assertIn("平均收益", output)
        self.assertIn("5日", output)

    def test_render_backtest_json_is_machine_readable(self):
        buf = StringIO()

        render_backtest_json(self.sample_backtest_report(), buf)

        data = json.loads(buf.getvalue())
        self.assertEqual(data["code"], "600519")
        self.assertEqual(data["sample_count"], 1)

    def test_load_portfolio_csv(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "portfolio.csv"
            path.write_text("code\n意华股份\n", encoding="utf-8")

            holdings = load_portfolio_csv(str(path))

        self.assertEqual(holdings[0][0], "意华股份")
        self.assertIsNone(holdings[0][1])

    def test_load_portfolio_csv_still_accepts_optional_position_columns(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "portfolio.csv"
            path.write_text("code,cost,position\n600519,1000,0.2\n", encoding="utf-8")

            holdings = load_portfolio_csv(str(path))

        self.assertEqual(holdings[0][1], Position(1000.0, 0.2))


if __name__ == "__main__":
    unittest.main()
