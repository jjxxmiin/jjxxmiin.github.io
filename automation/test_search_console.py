import datetime
import unittest

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


if __name__ == "__main__":
    unittest.main()
