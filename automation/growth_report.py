#!/usr/bin/env python3
"""Read GSC/GA4 and save two equal, non-overlapping periods privately.

Run from the repository root: python -m automation.growth_report
The three-day lag avoids comparing today's partial data with complete dates;
providers may still revise recent data. No API writes or publishing occur.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path

from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

from automation.build_zero_organic_manifest import ga4_client, find_credentials
from automation.search_console import SITE, client

ROOT = Path(__file__).resolve().parent.parent


def windows(end: date, days: int) -> dict:
    if days < 1:
        raise ValueError("days must be positive")
    start = end - timedelta(days=days - 1)
    return {
        "previous": (start - timedelta(days=days), start - timedelta(days=1)),
        "current": (start, end),
    }


def collect(gsc, ga4, start: date, end: date) -> dict:
    period = {"start": start.isoformat(), "end": end.isoformat()}
    result = gsc.searchanalytics().query(siteUrl=SITE, body={
        "startDate": period["start"], "endDate": period["end"],
        "dimensions": [], "dataState": "final",
    }).execute()
    # No row is missing data, not a measured zero.
    totals = next(iter(result.get("rows", [])), None)
    def report(dimensions, metrics):
        response = ga4.run_report(RunReportRequest(
            property="properties/463694693",
            date_ranges=[DateRange(start_date=period["start"], end_date=period["end"])],
            dimensions=[Dimension(name=name) for name in dimensions],
            metrics=[Metric(name=name) for name in metrics], limit=10000,
        ))
        if response.row_count > len(response.rows):
            raise RuntimeError("GA4 response truncated; refusing to save partial totals")
        return [dict(
            [(name, row.dimension_values[i].value) for i, name in enumerate(dimensions)] +
            [(name, int(row.metric_values[i].value)) for i, name in enumerate(metrics)]
        ) for row in response.rows]
    channels = report(["sessionDefaultChannelGroup", "country"], ["sessions", "engagedSessions"])
    events = report(["eventName"], ["eventCount"])
    return {
        "period": period, "gsc": totals,
        "organic_sessions": sum(r["sessions"] for r in channels if r["sessionDefaultChannelGroup"] == "Organic Search"),
        "korean_organic_sessions": sum(r["sessions"] for r in channels if r["sessionDefaultChannelGroup"] == "Organic Search" and r["country"] == "South Korea"),
        "channels_countries": channels,
        "book_events": {r["eventName"]: r["eventCount"] for r in events if r["eventName"].startswith("book_")},
    }


def markdown(data: dict) -> str:
    previous, current = data["previous"], data["current"]
    def cell(period, key):
        if key.startswith("gsc."):
            return (period["gsc"] or {}).get(key.split(".")[1], "데이터 없음")
        return period[key]
    lines = ["# OPSOAI 성장 점검", "",
             f"이전: {previous['period']['start']} ~ {previous['period']['end']}",
             f"현재: {current['period']['start']} ~ {current['period']['end']}", "",
             "| 지표 | 이전 | 현재 |", "| --- | ---: | ---: |"]
    for label, key in [("Google 검색 클릭", "gsc.clicks"), ("Google 검색 노출", "gsc.impressions"),
                       ("전체 자연검색 세션", "organic_sessions"), ("한국 자연검색 세션", "korean_organic_sessions")]:
        lines.append(f"| {label} | {cell(previous, key)} | {cell(current, key)} |")
    lines += ["", "## 읽기 이벤트", "", "| 이벤트 | 이전 | 현재 |", "| --- | ---: | ---: |"]
    for event in ("book_open", "book_complete", "book_share"):
        lines.append(f"| {event} | {previous['book_events'].get(event, '수집 없음')} | {current['book_events'].get(event, '수집 없음')} |")
    lines += ["", "2026-09-13 분석 함수 연결을 수정했다. 그 이전 읽기 이벤트의 부재를 완독률 0%로 해석하지 않는다.",
              "이벤트 건수는 고유 독자 수나 완독률이 아니다. Google 검색 클릭과 전체 검색 세션은 범위가 다르다.",
              "최근 데이터는 공급자가 수정할 수 있다. 수치가 적거나 기간에 수정 전후가 섞이면 효과 판단을 보류한다.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end", type=date.fromisoformat, default=date.today() - timedelta(days=3))
    parser.add_argument("--days", type=int, default=28)
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be positive")
    gsc, ga4 = client(), ga4_client(find_credentials(None))
    data = {name: collect(gsc, ga4, start, end) for name, (start, end) in windows(args.end, args.days).items()}
    data["captured_at"] = date.today().isoformat()
    output = ROOT / ".growth-state" / f"growth-{args.end}-{args.days}d"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(markdown(data), encoding="utf-8")
    print(output.with_suffix(".md"))


if __name__ == "__main__":
    main()
