import unittest

from astockdata.tencent import parse_tencent_response


def make_line(prefix_code, name, price, pe_ttm, pb, mcap):
    vals = [""] * 90
    vals[1] = name
    vals[3] = str(price)
    vals[4] = "1200.00"
    vals[5] = "1210.00"
    vals[31] = "12.10"
    vals[32] = "1.01"
    vals[33] = "1230.00"
    vals[34] = "1190.00"
    vals[37] = "123456.7"
    vals[38] = "0.58"
    vals[39] = str(pe_ttm)
    vals[43] = "3.35"
    vals[44] = str(mcap)
    vals[45] = "15100.00"
    vals[46] = str(pb)
    vals[47] = "1333.31"
    vals[48] = "1090.89"
    vals[49] = "0.88"
    vals[52] = "18.00"
    return f'v_{prefix_code}="' + "~".join(vals) + '";'


class TencentParserTests(unittest.TestCase):
    def test_parses_quote_fields_with_correct_indexes(self):
        raw = make_line("sh600519", "贵州茅台", "1212.10", "18.32", "5.66", "15152.24")

        quotes = parse_tencent_response(raw)

        self.assertEqual(len(quotes), 1)
        quote = quotes[0]
        self.assertEqual(quote.code, "600519")
        self.assertEqual(quote.name, "贵州茅台")
        self.assertEqual(quote.price, 1212.10)
        self.assertEqual(quote.pe_ttm, 18.32)
        self.assertEqual(quote.pb, 5.66)
        self.assertEqual(quote.market_cap_yi, 15152.24)

    def test_ignores_malformed_lines(self):
        raw = "\n".join(
            [
                "not a quote",
                make_line("sh600519", "贵州茅台", "1212.10", "18.32", "5.66", "15152.24"),
                'v_sz000001="too~short";',
            ]
        )

        quotes = parse_tencent_response(raw)

        self.assertEqual([q.code for q in quotes], ["600519"])


if __name__ == "__main__":
    unittest.main()

