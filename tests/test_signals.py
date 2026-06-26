import unittest

from astockdata.chan import CentralZone, ChanStructure, Fractal, Stroke
from astockdata.kline import KLine
from astockdata.market_context import MarketContext
from astockdata.resolver import StockIdentity
from astockdata.signals import ChanAnalyzer, ChanSignal, ChanSignalEngine, Position, map_signal_to_action, summarize_structure
from astockdata.technical_context import TechnicalContext
from astockdata.volume_context import VolumeContext


def kline(ts, open_, high, low, close):
    return KLine("600519", "1d", ts, open_, high, low, close, 100.0, 1000.0)


def market_context(label, score, summary):
    return MarketContext(
        label=label,
        score=score,
        index=None,
        industry="电子元件",
        sector=None,
        summary=summary,
        reasons=[summary],
        risk_notes=["大盘和板块都偏弱"] if label == "逆风" else [],
    )


def technical_context(label, momentum_label, bollinger_label, summary):
    return TechnicalContext(
        label=label,
        score=0.7 if label == "助力" else 0.32 if label == "拖累" else 0.5,
        momentum_label=momentum_label,
        momentum_score=0.7,
        ma20=None,
        ma20_slope_pct=None,
        roc5_pct=None,
        bollinger_label=bollinger_label,
        bollinger_width_pct=None,
        bollinger_width_percentile=None,
        summary=summary,
        reasons=[summary],
        risk_notes=["趋势动量走弱"] if label == "拖累" else [],
    )


def volume_context(label, volume_label, summary):
    return VolumeContext(
        label=label,
        score=0.68 if label == "助力" else 0.28 if label == "拖累" else 0.5,
        volume_label=volume_label,
        volume_ratio_5=1.6 if "放量" in volume_label else 0.7,
        volume_ratio_20=1.4,
        amount_ratio_5=1.5,
        turnover_pct=None,
        turnover_label="数据不足",
        summary=summary,
        reasons=[summary],
        risk_notes=[volume_label] if label == "拖累" else [],
    )


class SignalTests(unittest.TestCase):
    def make_structure(self, trend="uptrend", up_risk=False, down_repair=False):
        bottom = Fractal("bottom", "1", 10.0, 0)
        top = Fractal("top", "2", 15.0, 4)
        return ChanStructure(
            merged=[],
            fractals=[bottom, top],
            strokes=[Stroke(bottom, top, "up", 5.0, 100.0)],
            trend=trend,
            up_divergence_risk=up_risk,
            down_divergence_repair=down_repair,
        )

    def first_buy_structure(self):
        top1 = Fractal("top", "1", 20.0, 1)
        bottom1 = Fractal("bottom", "2", 10.0, 5)
        top2 = Fractal("top", "3", 16.0, 9)
        bottom2 = Fractal("bottom", "4", 8.0, 13)
        return ChanStructure(
            merged=[],
            fractals=[top1, bottom1, top2, bottom2],
            strokes=[
                Stroke(top1, bottom1, "down", 10.0, 100.0),
                Stroke(bottom1, top2, "up", 6.0, 100.0),
                Stroke(top2, bottom2, "down", 8.0, 100.0),
            ],
            trend="downtrend",
            up_divergence_risk=False,
            down_divergence_repair=True,
        )

    def third_buy_structure_inside_zone(self):
        bottom1 = Fractal("bottom", "1", 10.0, 1)
        top1 = Fractal("top", "2", 18.0, 5)
        bottom2 = Fractal("bottom", "3", 12.0, 9)
        top2 = Fractal("top", "4", 22.0, 13)
        bottom3 = Fractal("bottom", "5", 19.0, 17)
        zone = CentralZone("1", "3", 12.0, 18.0, 3, "up")
        return ChanStructure(
            merged=[],
            fractals=[bottom1, top1, bottom2, top2, bottom3],
            strokes=[
                Stroke(bottom1, top1, "up", 8.0, 100.0),
                Stroke(top1, bottom2, "down", 6.0, 100.0),
                Stroke(bottom2, top2, "up", 10.0, 100.0),
                Stroke(top2, bottom3, "down", 3.0, 100.0),
            ],
            zones=[zone],
            trend="uptrend",
            up_divergence_risk=False,
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
            stock_name="贵州茅台",
        )

        payload = signal.to_dict()
        self.assertEqual(payload["stock_name"], "贵州茅台")
        self.assertEqual(payload["strength_label"], "较强")
        self.assertEqual(payload["confirmation_status"], "有效确认")
        self.assertEqual(payload["daily_summary"]["trend_label"], "上升趋势")
        self.assertEqual(payload["daily_summary"]["stroke_count"], 1)
        self.assertEqual(payload["daily_summary"]["latest_bottom"]["price"], 10.0)
        self.assertEqual(payload["confirmation_summary"]["trend_label"], "上升趋势")

    def test_summarize_structure_includes_latest_central_zone(self):
        zone = CentralZone("2026-06-01", "2026-06-10", 12.0, 18.0, 3, "up")
        summary = summarize_structure(
            ChanStructure(
                merged=[],
                fractals=[],
                strokes=[],
                zones=[zone],
                trend="range",
                up_divergence_risk=False,
                down_divergence_repair=False,
            )
        )

        self.assertIsNotNone(summary.latest_zone)
        self.assertEqual(summary.latest_zone.low, 12.0)
        self.assertEqual(summary.latest_zone.high, 18.0)
        self.assertEqual(summary.latest_zone.position_label, "中枢上方")
        self.assertIn("脱离中枢上方", summary.latest_zone.meaning)

    def test_summarize_structure_uses_latest_price_for_zone_position(self):
        zone = CentralZone("2026-06-01", "2026-06-10", 12.0, 18.0, 3, "up")
        summary = summarize_structure(
            ChanStructure(
                merged=[],
                fractals=[],
                strokes=[],
                zones=[zone],
                trend="range",
                up_divergence_risk=False,
                down_divergence_repair=False,
            ),
            latest_price=15.0,
        )

        self.assertIsNotNone(summary.latest_zone)
        self.assertEqual(summary.latest_zone.position_label, "中枢内部")
        self.assertIn("仍在中枢内部", summary.latest_zone.meaning)

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

    def test_first_buy_trade_point_turns_downtrend_observation_into_buy_signal(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=None,
            latest_price=8.8,
        )

        payload = signal.to_dict()
        self.assertEqual(signal.signal, "试买入")
        self.assertEqual(signal.action, "买入")
        self.assertEqual(payload["trade_point"]["label"], "一买")
        self.assertEqual(payload["trade_point"]["action_bias"], "buy")
        self.assertIn("缠论买卖点：一买", "；".join(signal.reasons))
        self.assertEqual(payload["trade_point_replay"]["label"], "一买")

    def test_buy_signal_is_rewritten_to_observe_when_vetoed(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.third_buy_structure_inside_zone(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=15.0,
        )

        self.assertEqual(signal.action, "继续持有")
        self.assertEqual(signal.signal, "观察")
        self.assertTrue(signal.veto_context.vetoed)
        self.assertEqual(signal.veto_context.original_action, "买入")
        self.assertIn("买入被否决", "；".join(signal.reasons))
        self.assertLessEqual(signal.confidence, 0.48)

    def test_first_buy_is_not_vetoed_by_downtrend_repair(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=8.8,
        )

        self.assertEqual(signal.action, "买入")
        self.assertFalse(signal.veto_context.vetoed)

    def test_headwind_market_context_degrades_buy_confidence(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=8.8,
            market_context=market_context("逆风", 0.3, "沪深300下跌1.40%；电子元件下跌2.00%"),
        )

        payload = signal.to_dict()
        self.assertEqual(payload["market_context"]["label"], "逆风")
        self.assertLess(signal.confidence, 0.78)
        self.assertIn("市场环境逆风", "；".join(signal.risk_notes))

    def test_tailwind_market_context_adds_reason_to_buy_signal(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=8.8,
            market_context=market_context("顺风", 0.72, "沪深300上涨1.20%；电子元件上涨2.40%"),
        )

        self.assertGreaterEqual(signal.confidence, 0.8)
        self.assertIn("市场环境顺风", "；".join(signal.reasons))

    def test_supportive_technical_context_adds_reason_to_buy_signal(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=8.8,
            technical_context=technical_context("助力", "动量向上", "正常波动", "趋势动量向上；布林正常波动"),
        )

        payload = signal.to_dict()
        self.assertEqual(payload["technical_context"]["label"], "助力")
        self.assertGreaterEqual(signal.confidence, 0.8)
        self.assertIn("辅助确认偏正面", "；".join(signal.reasons))

    def test_weak_technical_context_degrades_buy_confidence(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=8.8,
            technical_context=technical_context("拖累", "动量走弱", "正常波动", "趋势动量走弱；布林正常波动"),
        )

        self.assertLess(signal.confidence, 0.78)
        self.assertIn("辅助确认偏负面", "；".join(signal.risk_notes))

    def test_supportive_volume_context_adds_reason_to_buy_signal(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=8.8,
            volume_context=volume_context("助力", "放量上涨", "放量上涨：买盘参与更主动"),
        )

        payload = signal.to_dict()
        self.assertEqual(payload["volume_context"]["label"], "助力")
        self.assertIn("量能确认偏正面", "；".join(signal.reasons))

    def test_volume_surge_down_vetoes_buy_signal(self):
        engine = ChanSignalEngine()

        signal = engine.evaluate(
            "600519",
            daily_structure=self.first_buy_structure(),
            confirm_structure=self.make_structure("uptrend"),
            latest_price=8.8,
            volume_context=volume_context("拖累", "放量下跌", "放量下跌：抛压增强"),
        )

        self.assertEqual(signal.action, "继续持有")
        self.assertTrue(signal.veto_context.vetoed)
        self.assertIn("放量下跌", "；".join(signal.veto_context.reasons))

    def test_analyzer_uses_resolved_code_for_market_context(self):
        class FakeResolver:
            def resolve(self, query):
                return StockIdentity(code="002897", name="意华股份", query=query)

        class FakeKLineProvider:
            def daily_klines(self, code):
                return [
                    kline("2026-06-22", 10, 11, 9, 10.5),
                    kline("2026-06-23", 10.5, 12, 10, 11.2),
                    kline("2026-06-24", 11.2, 12.5, 10.8, 12.0),
                ]

            def intraday_klines(self, code, frequency):
                return []

        class FakeMarketContextProvider:
            def __init__(self):
                self.codes = []

            def context_for(self, code):
                self.codes.append(code)
                return market_context("中性", 0.5, "沪深300上涨0.10%；通信设备暂未匹配到行业板块")

        class FakeEngine:
            def evaluate(self, **kwargs):
                return ChanSignal(
                    code=kwargs["code"],
                    stock_name=kwargs["stock_name"],
                    action="继续持有",
                    signal="观察",
                    confidence=0.5,
                    confirmed=True,
                    intraday=False,
                    confirmation_missing=True,
                    reasons=[],
                    invalidations=[],
                    risk_notes=[],
                    market_context=kwargs["market_context"],
                    technical_context=kwargs["technical_context"],
                )

        market_provider = FakeMarketContextProvider()
        analyzer = ChanAnalyzer(
            kline_provider=FakeKLineProvider(),
            confirm_provider=FakeKLineProvider(),
            engine=FakeEngine(),
            resolver=FakeResolver(),
            market_context_provider=market_provider,
        )

        signal = analyzer.analyze("意华股份")

        self.assertEqual(signal.code, "002897")
        self.assertEqual(market_provider.codes, ["002897"])
        self.assertIsNotNone(signal.technical_context)

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
