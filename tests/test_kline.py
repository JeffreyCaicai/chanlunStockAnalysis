import unittest

from astockdata.kline import KLine, parse_baidu_kline_response


class KLineTests(unittest.TestCase):
    def test_parse_baidu_kline_response_maps_rows_to_klines(self):
        payload = {
            "Result": {
                "newMarketData": {
                    "keys": ["time", "open", "close", "high", "low", "volume", "amount"],
                    "marketData": "20260620,10,11,12,9,100,1000;20260621,11,12,13,10,120,1500",
                }
            }
        }

        rows = parse_baidu_kline_response("600519", "1d", payload)

        self.assertEqual(
            rows,
            [
                KLine("600519", "1d", "20260620", 10.0, 12.0, 9.0, 11.0, 100.0, 1000.0),
                KLine("600519", "1d", "20260621", 11.0, 13.0, 10.0, 12.0, 120.0, 1500.0),
            ],
        )

    def test_parse_baidu_kline_response_ignores_short_rows(self):
        payload = {
            "Result": {
                "newMarketData": {
                    "keys": ["time", "open", "close", "high", "low", "volume", "amount"],
                    "marketData": "bad,row;20260621,11,12,13,10,120,1500",
                }
            }
        }

        rows = parse_baidu_kline_response("600519", "1d", payload)

        self.assertEqual([row.timestamp for row in rows], ["20260621"])


if __name__ == "__main__":
    unittest.main()

