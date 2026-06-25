import json
import unittest
from io import StringIO

from astockdata.cli import render_json, render_table
from astockdata.models import ValuationResult


class CliRenderTests(unittest.TestCase):
    def sample_result(self):
        return ValuationResult(
            code="600519",
            name="贵州茅台",
            industry="白酒Ⅱ",
            price=1212.1,
            pe_ttm=18.32,
            pb=5.66,
            market_cap_yi=15152.24,
            eps_this_year=65.0,
            eps_next_year=70.0,
            eps_report_count=5,
            forward_pe=18.65,
            growth_pct=7.69,
            peg=2.42,
            pe_digest_years=0.0,
            rating_summary={"买入": 3, "增持": 2},
            latest_reports=[],
        )

    def test_render_json_is_machine_readable(self):
        buf = StringIO()

        render_json([self.sample_result()], buf)

        data = json.loads(buf.getvalue())
        self.assertEqual(data[0]["code"], "600519")
        self.assertEqual(data[0]["rating_summary"]["买入"], 3)

    def test_render_table_contains_core_columns(self):
        buf = StringIO()

        render_table([self.sample_result()], buf)

        output = buf.getvalue()
        self.assertIn("代码", output)
        self.assertIn("贵州茅台", output)
        self.assertIn("PEG", output)
        self.assertIn("15152.24", output)


if __name__ == "__main__":
    unittest.main()

