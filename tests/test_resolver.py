import unittest

from astockdata.resolver import EastmoneyStockResolver, StockIdentity


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=10):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return self.responses.pop(0)


class ResolverTests(unittest.TestCase):
    def test_resolves_stock_name_with_eastmoney_suggest(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "QuotationCodeTable": {
                            "Data": [
                                {"Code": "688017", "Name": "绿的谐波", "QuoteID": "1.688017"},
                            ]
                        }
                    }
                )
            ]
        )
        resolver = EastmoneyStockResolver(session=session)

        identity = resolver.resolve("绿的谐波")

        self.assertEqual(identity, StockIdentity(code="688017", name="绿的谐波", query="绿的谐波"))
        self.assertEqual(session.calls[0]["params"]["input"], "绿的谐波")

    def test_resolves_code_to_name_when_search_succeeds(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "QuotationCodeTable": {
                            "Data": [
                                {"Code": "002897", "Name": "意华股份", "QuoteID": "0.002897"},
                            ]
                        }
                    }
                )
            ]
        )
        resolver = EastmoneyStockResolver(session=session)

        identity = resolver.resolve("002897")

        self.assertEqual(identity.code, "002897")
        self.assertEqual(identity.name, "意华股份")

    def test_code_input_falls_back_when_name_lookup_fails(self):
        class BrokenSession:
            def get(self, *args, **kwargs):
                raise RuntimeError("network down")

        resolver = EastmoneyStockResolver(session=BrokenSession())

        identity = resolver.resolve("sh600519")

        self.assertEqual(identity.code, "600519")
        self.assertEqual(identity.name, "")

    def test_name_input_requires_search_result(self):
        resolver = EastmoneyStockResolver(session=FakeSession([FakeResponse({"QuotationCodeTable": {"Data": []}})]))

        with self.assertRaises(ValueError):
            resolver.resolve("不存在的股票名")


if __name__ == "__main__":
    unittest.main()
