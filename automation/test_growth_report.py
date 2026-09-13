from datetime import date

import pytest

from automation.growth_report import markdown, windows


def test_comparison_has_equal_complete_nonoverlapping_dates():
    periods = windows(date(2026, 9, 10), 28)
    assert periods["current"] == (date(2026, 8, 14), date(2026, 9, 10))
    assert periods["previous"] == (date(2026, 7, 17), date(2026, 8, 13))
    with pytest.raises(ValueError):
        windows(date(2026, 9, 10), 0)


def test_missing_measurements_are_not_reported_as_zero():
    period = {"period": {"start": "2026-08-14", "end": "2026-09-10"},
              "gsc": None, "organic_sessions": 0, "korean_organic_sessions": 0, "book_events": {}}
    result = markdown({"previous": period, "current": period})
    assert "Google 검색 클릭 | 데이터 없음 | 데이터 없음" in result
    assert "book_complete | 수집 없음 | 수집 없음" in result
