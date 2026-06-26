import unittest

from astockdata.chan import CentralZone, ChanStructure, Fractal, Stroke
from astockdata.chan_points import TradePoint
from astockdata.market_context import MarketContext
from astockdata.technical_context import TechnicalContext
from astockdata.veto import evaluate_buy_veto


def fractal(kind, ts, price, index):
    return Fractal(kind, ts, float(price), index)


def stroke(start, end):
    direction = "up" if start.kind == "bottom" and end.kind == "top" else "down"
    return Stroke(start, end, direction, abs(end.price - start.price), 100.0)


def structure(trend="uptrend", zone=None):
    bottom = fractal("bottom", "1", 10, 1)
    top = fractal("top", "2", 20, 5)
    return ChanStructure(
        merged=[],
        fractals=[bottom, top],
        strokes=[stroke(bottom, top)],
        zones=[zone] if zone else [],
        trend=trend,
        up_divergence_risk=False,
        down_divergence_repair=False,
    )


def trade_point(kind="third_buy", label="三买", invalidation="-"):
    return TradePoint(kind, label, "buy", "2", 20.0, 0.74, "买点候选", invalidation)


def market(label):
    return MarketContext(label, 0.3 if label == "逆风" else 0.5, None, "", None, label, [label], [])


def technical(label, bollinger="正常波动"):
    return TechnicalContext(
        label=label,
        score=0.3 if label == "拖累" else 0.5,
        momentum_label="动量走弱" if label == "拖累" else "动量中性",
        momentum_score=0.3 if label == "拖累" else 0.5,
        ma20=None,
        ma20_slope_pct=None,
        roc5_pct=None,
        bollinger_label=bollinger,
        bollinger_width_pct=None,
        bollinger_width_percentile=None,
        summary=label,
        reasons=[label],
        risk_notes=[],
    )


class BuyVetoTests(unittest.TestCase):
    def test_vetoes_third_buy_when_price_falls_back_into_zone(self):
        zone = CentralZone("1", "3", 12.0, 18.0, 3, "up")

        veto = evaluate_buy_veto(
            signal="强买入",
            action="买入",
            latest_price=15.0,
            structure=structure(zone=zone),
            trade_point=trade_point(),
            confirmation_missing=False,
        )

        self.assertTrue(veto.vetoed)
        self.assertEqual(veto.level, "hard")
        self.assertIn("三买后价格重新回到中枢", veto.summary)

    def test_vetoes_downward_bollinger_breakout(self):
        veto = evaluate_buy_veto(
            signal="强买入",
            action="买入",
            latest_price=20.0,
            structure=structure(),
            trade_point=trade_point("first_buy", "一买"),
            confirmation_missing=False,
            technical_context=technical("拖累", "压缩后向下突破"),
        )

        self.assertTrue(veto.vetoed)
        self.assertEqual(veto.level, "hard")
        self.assertIn("布林压缩后向下突破", "；".join(veto.reasons))

    def test_combines_market_headwind_and_technical_drag(self):
        veto = evaluate_buy_veto(
            signal="强买入",
            action="买入",
            latest_price=20.0,
            structure=structure(),
            trade_point=trade_point("second_buy", "二买"),
            confirmation_missing=False,
            market_context=market("逆风"),
            technical_context=technical("拖累"),
        )

        self.assertTrue(veto.vetoed)
        self.assertEqual(veto.level, "combined")
        self.assertIn("市场逆风叠加技术拖累", "；".join(veto.reasons))

    def test_does_not_veto_non_buy_action(self):
        veto = evaluate_buy_veto(
            signal="观察",
            action="继续持有",
            latest_price=20.0,
            structure=structure(trend="downtrend"),
            trade_point=None,
            confirmation_missing=False,
            technical_context=technical("拖累", "压缩后向下突破"),
        )

        self.assertFalse(veto.vetoed)
        self.assertEqual(veto.level, "none")


if __name__ == "__main__":
    unittest.main()
