#!/usr/bin/env python3
"""Build the fixed 90-day manifest of posts with zero organic landings.

This script intentionally answers a narrower question than "which posts have no
traffic today?":

* GA4 window: 2026-05-27 through 2026-08-24 (90 inclusive dates)
* channel: ``Organic Search``
* metric: landing sessions
* cohort: posts published *before* 2026-05-27, so every eligible post had the
  complete observation window

The default invocation is read-only except for the manifest it writes::

    python automation/build_zero_organic_manifest.py

Use ``--output -`` to print JSON without writing a file.  The script exits
without replacing the output when the target count is not the expected 447;
that guard keeps a partial API response or a URL-mapping regression from
silently changing the rewrite scope.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable

import yaml
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROPERTY_ID = "463694693"
DEFAULT_START = dt.date(2026, 5, 27)
DEFAULT_END = dt.date(2026, 8, 24)
DEFAULT_OUTPUT = ROOT / "automation/data/zero_organic_manifest.json"
DEFAULT_EXPECTED_TARGETS = 447
GA4_READONLY_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"

# This was a one-off diagnostic post, not a page in the measured cohort.  Keep
# the explicit exclusions anyway so backdating or renaming metadata cannot
# accidentally turn it into a rewrite target later.
EXCLUDED_SOURCES = {
    "_posts/2026-08-24-blog-514-posts-447-zero-organic-traffic.md",
}
EXCLUDED_PATHS = {
    "/posts/blog-514-posts-447-zero-organic-traffic/",
}

FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL
)
POST_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$")


def inclusive_days(start: dt.date, end: dt.date) -> int:
    """Return the number of calendar dates in an inclusive window."""
    if end < start:
        raise ValueError("관측 종료일은 시작일보다 빠를 수 없습니다.")
    return (end - start).days + 1


def parse_date(value: Any, *, source: str) -> dt.date:
    """Parse the Jekyll front-matter date without changing its timezone."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", str(value or ""))
    if not match:
        raise ValueError(f"{source}: front matter date를 해석할 수 없습니다: {value!r}")
    return dt.date.fromisoformat(match.group(1))


def jekyll_slugify(raw_slugs: list[str], *, root: Path = ROOT) -> list[str]:
    """Use the repository's Jekyll version for exact ``:title`` slugs."""
    ruby = (
        "require 'json'; require 'jekyll'; "
        "raw = JSON.parse(STDIN.read); "
        "puts JSON.generate(raw.map { |slug| "
        "Jekyll::Utils.slugify(slug, mode: 'default', cased: true) })"
    )
    try:
        result = subprocess.run(
            ["bundle", "exec", "ruby", "-e", ruby],
            cwd=root,
            input=json.dumps(raw_slugs, ensure_ascii=False),
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("bundle 또는 ruby를 찾지 못했습니다.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout).strip()[-800:]
        raise RuntimeError(f"Jekyll slug 생성 실패: {detail}") from exc

    values = json.loads(result.stdout)
    if not isinstance(values, list) or len(values) != len(raw_slugs):
        raise RuntimeError("Jekyll slug 결과 개수가 입력과 다릅니다.")
    return [str(value) for value in values]


def load_post_inventory(*, root: Path = ROOT) -> list[dict[str, str]]:
    """Read published Markdown posts and resolve their public Jekyll paths."""
    pending: list[tuple[str, str, str, dt.date, str]] = []
    for post_file in sorted((root / "_posts").glob("*.md")):
        source = post_file.relative_to(root).as_posix()
        text = post_file.read_text(encoding="utf-8")
        match = FRONT_MATTER_RE.match(text)
        if not match:
            raise ValueError(f"{source}: YAML front matter를 찾지 못했습니다.")
        data = yaml.safe_load(match.group(1)) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{source}: YAML front matter가 객체가 아닙니다.")
        # Match Jekyll and the original traffic audit: only boolean false hides
        # a post.  The string "false" is not treated as the boolean value.
        if data.get("published") is False:
            continue

        filename_match = POST_FILENAME_RE.match(post_file.name)
        if not filename_match:
            raise ValueError(f"{source}: Jekyll post 파일명 형식이 아닙니다.")
        published = parse_date(data.get("date"), source=source)
        title = str(data.get("title") or "").strip()
        if not title:
            raise ValueError(f"{source}: title이 비어 있습니다.")
        pending.append((source, filename_match.group(1), title, published, hashlib.sha256(text.encode("utf-8")).hexdigest()))

    slugs = jekyll_slugify([row[1] for row in pending], root=root)
    inventory = [
        {
            "source": source,
            "title": title,
            "date": published.isoformat(),
            "path": f"/posts/{slug}/",
            "original_sha256": original_sha256,
        }
        for (source, _raw_slug, title, published, original_sha256), slug in zip(pending, slugs)
    ]

    paths = [row["path"] for row in inventory]
    if len(paths) != len(set(paths)):
        duplicates = sorted(path for path in set(paths) if paths.count(path) > 1)
        raise ValueError(f"중복된 공개 post path가 있습니다: {duplicates[:10]}")
    return inventory


def find_credentials(explicit: str | None, *, root: Path = ROOT) -> Path:
    """Resolve a service-account key path without ever printing its content."""
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        candidates.append(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    candidates.extend(sorted(glob.glob(str(root / "teachingflow-*.json"))))

    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            return path
    raise FileNotFoundError(
        "GA4 서비스 계정 키를 찾지 못했습니다. --credentials 또는 "
        "GOOGLE_APPLICATION_CREDENTIALS를 지정하세요."
    )


def ga4_client(credentials_path: Path) -> BetaAnalyticsDataClient:
    credentials = service_account.Credentials.from_service_account_file(
        str(credentials_path), scopes=[GA4_READONLY_SCOPE]
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def fetch_organic_landing_rows(
    client: BetaAnalyticsDataClient,
    *,
    property_id: str,
    start: dt.date,
    end: dt.date,
) -> list[dict[str, str]]:
    """Fetch every Organic Search landing-page row from GA4."""
    rows: list[dict[str, str]] = []
    offset = 0
    page_size = 100_000
    while True:
        response = client.run_report(
            RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=[
                    DateRange(start_date=start.isoformat(), end_date=end.isoformat())
                ],
                dimensions=[Dimension(name="landingPagePlusQueryString")],
                metrics=[Metric(name="sessions")],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="sessionDefaultChannelGroup",
                        string_filter=Filter.StringFilter(
                            match_type=Filter.StringFilter.MatchType.EXACT,
                            value="Organic Search",
                        ),
                    )
                ),
                order_bys=[
                    OrderBy(
                        dimension=OrderBy.DimensionOrderBy(
                            dimension_name="landingPagePlusQueryString"
                        )
                    )
                ],
                offset=offset,
                limit=page_size,
            )
        )
        page = [
            {
                "landingPagePlusQueryString": row.dimension_values[0].value,
                "sessions": row.metric_values[0].value,
            }
            for row in response.rows
        ]
        rows.extend(page)
        offset += len(page)
        if not page or offset >= response.row_count:
            break
    return rows


def paths_with_sessions(rows: Iterable[dict[str, str]]) -> set[str]:
    """Collapse GA4 query-string variants into public URL paths."""
    sessions_by_path: dict[str, float] = {}
    for row in rows:
        raw_path = row.get("landingPagePlusQueryString", "")
        path = raw_path.split("?", 1)[0]
        try:
            sessions = float(row.get("sessions", "0"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"GA4 sessions 값이 숫자가 아닙니다: {row!r}") from exc
        sessions_by_path[path] = sessions_by_path.get(path, 0.0) + sessions
    return {path for path, sessions in sessions_by_path.items() if sessions > 0}


def build_manifest(
    inventory: list[dict[str, str]],
    organic_paths: set[str],
    *,
    property_id: str,
    start: dt.date,
    end: dt.date,
) -> dict[str, Any]:
    eligible = [
        row
        for row in inventory
        if dt.date.fromisoformat(row["date"]) < start
        and row["source"] not in EXCLUDED_SOURCES
        and row["path"] not in EXCLUDED_PATHS
    ]
    with_organic = [row for row in eligible if row["path"] in organic_paths]
    targets = sorted(
        (row for row in eligible if row["path"] not in organic_paths),
        key=lambda row: (row["date"], row["source"]),
    )
    inventory_paths = {row["path"] for row in inventory}

    return {
        "schema_version": 1,
        "measurement": {
            "source": "Google Analytics 4 Data API",
            "property_id": property_id,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "inclusive_days": inclusive_days(start, end),
            "channel_filter": {
                "dimension": "sessionDefaultChannelGroup",
                "match": "EXACT",
                "value": "Organic Search",
            },
            "landing_dimension": "landingPagePlusQueryString",
            "metric": "sessions",
            "query_strings_removed_before_path_match": True,
        },
        "cohort": {
            "rule": "front matter date is strictly before start_date",
            "excluded_sources": sorted(EXCLUDED_SOURCES),
            "excluded_paths": sorted(EXCLUDED_PATHS),
        },
        "summary": {
            "published_posts_in_inventory": len(inventory),
            "eligible_full_window_posts": len(eligible),
            "eligible_posts_with_organic_landing_session": len(with_organic),
            "eligible_posts_with_zero_organic_landing_session": len(targets),
            "organic_paths_not_in_current_inventory": len(organic_paths - inventory_paths),
        },
        "targets": targets,
    }


def write_json_atomic(data: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, output)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--property-id", default=DEFAULT_PROPERTY_ID)
    parser.add_argument("--start", type=dt.date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=dt.date.fromisoformat, default=DEFAULT_END)
    parser.add_argument("--credentials", help="GA4 서비스 계정 JSON 경로")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="manifest JSON 경로. stdout은 '-' (기본: %(default)s)",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=DEFAULT_EXPECTED_TARGETS,
        help="이 개수와 다르면 출력 파일을 바꾸지 않고 실패 (기본: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        days = inclusive_days(args.start, args.end)
        if days != 90:
            raise ValueError(f"관측 창은 정확히 90일이어야 합니다. 현재 {days}일입니다.")
        inventory = load_post_inventory()
        credentials_path = find_credentials(args.credentials)
        rows = fetch_organic_landing_rows(
            ga4_client(credentials_path),
            property_id=args.property_id,
            start=args.start,
            end=args.end,
        )
        manifest = build_manifest(
            inventory,
            paths_with_sessions(rows),
            property_id=args.property_id,
            start=args.start,
            end=args.end,
        )
        actual = manifest["summary"][
            "eligible_posts_with_zero_organic_landing_session"
        ]
        if actual != args.expected_count:
            raise ValueError(
                f"대상 수가 예상과 다릅니다: expected={args.expected_count}, actual={actual}. "
                "출력 파일을 갱신하지 않았습니다."
            )

        if args.output == "-":
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
        else:
            output = Path(args.output)
            if not output.is_absolute():
                output = ROOT / output
            write_json_atomic(manifest, output)
            print(f"manifest: {output.relative_to(ROOT)}")
        summary = manifest["summary"]
        print(
            "cohort: "
            f"eligible={summary['eligible_full_window_posts']}, "
            f"organic={summary['eligible_posts_with_organic_landing_session']}, "
            f"zero={actual}",
            file=sys.stderr if args.output == "-" else sys.stdout,
        )
        return 0
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
