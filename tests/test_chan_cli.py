import json
import tempfile
import unittest
from io import StringIO
from pathlib import Path

from astockdata.chan_cli import load_portfolio_csv, render_json, render_table
from astockdata.signals import ChanSignal, Position


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
            position_context=Position(cost=1000.0, position=0.2),
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
        self.assertIn("信号力度", output)
        self.assertIn("较强", output)
        self.assertIn("继续持有", output)
        self.assertIn("日线结构未破坏", output)

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
