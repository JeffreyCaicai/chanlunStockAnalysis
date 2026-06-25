import unittest

from astockdata.chan import analyze_structure, build_strokes, detect_fractals, merge_inclusions
from astockdata.kline import KLine


def kline(ts, open_, high, low, close, volume=100):
    return KLine("600519", "1d", ts, open_, high, low, close, float(volume), float(volume * close))


class ChanStructureTests(unittest.TestCase):
    def test_merge_inclusions_combines_contained_klines(self):
        rows = [
            kline("1", 10, 12, 9, 11),
            kline("2", 11, 11.5, 9.5, 10),
            kline("3", 10, 13, 10, 12),
        ]

        merged = merge_inclusions(rows)

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0].high, 12)
        self.assertEqual(merged[0].low, 9.5)
        self.assertEqual(merged[0].source_indices, [0, 1])

    def test_detect_fractals_finds_top_and_bottom(self):
        rows = [
            kline("1", 10, 11, 9, 10),
            kline("2", 10, 13, 11, 12),
            kline("3", 12, 12, 10, 11),
            kline("4", 11, 10, 7, 8),
            kline("5", 8, 11, 8, 10),
        ]

        fractals = detect_fractals(merge_inclusions(rows))

        self.assertEqual([(f.kind, f.timestamp) for f in fractals], [("top", "2"), ("bottom", "4")])

    def test_build_strokes_keeps_alternating_extreme_fractals(self):
        rows = [
            kline("1", 10, 11, 9, 10),
            kline("2", 10, 13, 11, 12),
            kline("3", 12, 12, 10, 11),
            kline("4", 11, 10, 7, 8),
            kline("5", 8, 11, 8, 10),
            kline("6", 10, 15, 12, 14),
            kline("7", 14, 13, 11, 12),
        ]
        fractals = detect_fractals(merge_inclusions(rows))

        strokes = build_strokes(fractals, min_gap=1)

        self.assertEqual([s.direction for s in strokes], ["down", "up"])
        self.assertEqual(strokes[0].start.kind, "top")
        self.assertEqual(strokes[0].end.kind, "bottom")

    def test_analyze_structure_classifies_uptrend_and_divergence_risk(self):
        rows = [
            kline("1", 10, 11, 9, 10, 200),
            kline("2", 10, 13, 11, 12, 200),
            kline("3", 12, 12, 10, 11, 180),
            kline("4", 11, 10, 7, 8, 160),
            kline("5", 8, 11, 8, 10, 140),
            kline("6", 10, 15, 12, 14, 120),
            kline("7", 14, 13, 11, 12, 100),
            kline("8", 12, 13, 10, 11, 100),
            kline("9", 11, 14, 11, 13, 80),
            kline("10", 13, 16, 14, 15, 60),
            kline("11", 15, 15, 13, 14, 50),
        ]

        structure = analyze_structure(rows, min_gap=1)

        self.assertEqual(structure.trend, "uptrend")
        self.assertTrue(structure.up_divergence_risk)


if __name__ == "__main__":
    unittest.main()
