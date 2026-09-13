import datetime
import unittest
from unittest import mock

import search_console


class SearchConsoleDateWindowTests(unittest.TestCase):
    def test_ninety_day_window_is_exactly_ninety_inclusive_dates(self):
        start, end = search_console.date_window(
            90,
            today=datetime.date(2026, 8, 24),
        )
        self.assertEqual(start, datetime.date(2026, 5, 27))
        self.assertEqual(end, datetime.date(2026, 8, 24))
        self.assertEqual((end - start).days + 1, 90)

    def test_window_rejects_non_positive_days(self):
        with self.assertRaises(ValueError):
            search_console.date_window(0)


class SearchConsoleAudienceTests(unittest.TestCase):
    def test_query_report_excludes_site_searches_before_limiting_rows(self):
        svc = mock.Mock()
        svc.searchanalytics.return_value.query.return_value.execute.return_value = {"rows": []}
        search_console.query(svc, 28, ["query", "page"])
        body = svc.searchanalytics.return_value.query.call_args.kwargs["body"]
        self.assertEqual(body["dimensionFilterGroups"][0]["filters"][0], {
            "dimension": "query", "operator": "notContains", "expression": "site:"
        })
        search_console.query(svc, 28, ["page"])
        body = svc.searchanalytics.return_value.query.call_args.kwargs["body"]
        self.assertNotIn("dimensionFilterGroups", body)


if __name__ == "__main__":
    unittest.main()
