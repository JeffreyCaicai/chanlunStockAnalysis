import unittest

from astockdata.eastmoney import EastmoneyClient, parse_report, parse_stock_info


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, headers=None, timeout=15, **kwargs):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )
        return self.responses.pop(0)


class EastmoneyParserTests(unittest.TestCase):
    def test_parses_stock_info(self):
        data = {
            "f57": "688017",
            "f58": "绿的谐波",
            "f84": 183253582,
            "f85": 183253582,
            "f127": "自动化设备",
            "f116": 71682000000,
            "f117": 71682000000,
            "f189": 20200828,
            "f43": 391.0,
        }

        info = parse_stock_info(data)

        self.assertEqual(info.code, "688017")
        self.assertEqual(info.industry, "自动化设备")
        self.assertEqual(info.market_cap_yi, 716.82)
        self.assertEqual(info.list_date, "20200828")

    def test_parses_research_report_eps_fields(self):
        row = {
            "infoCode": "ABC",
            "publishDate": "2026-05-26 00:00:00",
            "orgSName": "国信证券",
            "title": "2026年一季度业绩快速增长",
            "emRatingName": "增持",
            "predictThisYearEps": "1.0300000000",
            "predictNextYearEps": "1.3600000000",
            "predictNextTwoYearEps": "",
        }

        report = parse_report(row)

        self.assertEqual(report.info_code, "ABC")
        self.assertEqual(report.publish_date, "2026-05-26")
        self.assertEqual(report.org, "国信证券")
        self.assertEqual(report.eps_this_year, 1.03)
        self.assertEqual(report.eps_next_year, 1.36)
        self.assertIsNone(report.eps_next_two_year)

    def test_stock_info_uses_eastmoney_secid_and_default_headers(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "data": {
                            "f57": "600519",
                            "f58": "贵州茅台",
                            "f84": 0,
                            "f85": 0,
                            "f127": "白酒Ⅱ",
                            "f116": 1515224000000,
                            "f117": 1510000000000,
                            "f189": 20010827,
                            "f43": 1212.1,
                        }
                    }
                )
            ]
        )
        client = EastmoneyClient(session=session, min_interval=0)

        info = client.stock_info("600519")

        self.assertEqual(info.name, "贵州茅台")
        self.assertEqual(session.calls[0]["params"]["secid"], "1.600519")
        self.assertIn("f127", session.calls[0]["params"]["fields"])

    def test_reports_fetches_pages_until_empty(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "data": [
                            {
                                "infoCode": "A",
                                "publishDate": "2026-05-26 00:00:00",
                                "orgSName": "国信证券",
                                "title": "报告一",
                                "emRatingName": "增持",
                                "predictThisYearEps": "1.03",
                                "predictNextYearEps": "1.36",
                            }
                        ],
                        "TotalPage": 2,
                    }
                ),
                FakeResponse({"data": [], "TotalPage": 2}),
            ]
        )
        client = EastmoneyClient(session=session, min_interval=0)

        reports = client.reports("688017", max_pages=2)

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].title, "报告一")
        self.assertEqual(session.calls[0]["params"]["qType"], "0")
        self.assertEqual(session.calls[0]["params"]["code"], "688017")


if __name__ == "__main__":
    unittest.main()

