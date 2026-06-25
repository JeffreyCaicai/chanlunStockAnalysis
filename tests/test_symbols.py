import unittest

from astockdata.symbols import market_prefix, normalize_code, secid


class SymbolTests(unittest.TestCase):
    def test_normalizes_common_a_share_formats(self):
        self.assertEqual(normalize_code("688017"), "688017")
        self.assertEqual(normalize_code("SH688017"), "688017")
        self.assertEqual(normalize_code("688017.SH"), "688017")
        self.assertEqual(normalize_code("sz000001"), "000001")
        self.assertEqual(normalize_code("BJ832000"), "832000")

    def test_rejects_invalid_codes(self):
        with self.assertRaises(ValueError):
            normalize_code("AAPL")

        with self.assertRaises(ValueError):
            normalize_code("12345")

    def test_market_prefix_and_eastmoney_secid(self):
        self.assertEqual(market_prefix("600519"), "sh")
        self.assertEqual(market_prefix("688017"), "sh")
        self.assertEqual(market_prefix("000001"), "sz")
        self.assertEqual(market_prefix("832000"), "bj")

        self.assertEqual(secid("600519"), "1.600519")
        self.assertEqual(secid("000001"), "0.000001")
        self.assertEqual(secid("832000"), "0.832000")


if __name__ == "__main__":
    unittest.main()

