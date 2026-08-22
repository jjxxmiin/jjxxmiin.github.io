#!/usr/bin/env python3
"""Search Console에서 실제 검색 쿼리를 뽑는다.

GA4는 "어느 페이지로 들어왔는가"까지만 알려주고 "무슨 말을 검색했는가"는 안 준다.
521편이 검색 유입 0인 이유를 알려면 노출(impressions)을 봐야 하는데, 그건
Search Console에만 있다. 특히 아래 두 가지가 목적이다.

  1. 노출은 있는데 클릭이 없는 쿼리  -> 제목만 고쳐서 되살릴 글을 찾는다.
  2. 순위 11~30위 쿼리              -> 조금만 보강하면 1페이지로 올릴 글을 찾는다.

사전 준비 (한 번만)
  1) API 활성화:
     gcloud services enable searchconsole.googleapis.com --project=teachingflow
     (또는 https://console.cloud.google.com/apis/library/searchconsole.googleapis.com)
  2) Search Console에서 서비스 계정에 권한 부여:
     search.google.com/search-console -> 설정 -> 사용자 및 권한 -> 사용자 추가
     agent-231@teachingflow.iam.gserviceaccount.com / 전체 또는 제한 권한

사용
    python automation/search_console.py --days 90
    python automation/search_console.py --days 90 --report ctr      # 제목 고칠 후보
    python automation/search_console.py --days 90 --report striking # 11~30위 기회
    python automation/search_console.py --days 90 --report pages
"""

from __future__ import annotations

import argparse
import datetime
import glob
import os
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 도메인 속성으로 등록돼 있다. URL 접두어 속성이면 "https://www.opsoai.com/" 형태다.
SITE = "sc-domain:opsoai.com"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


def client():
    keys = sorted(glob.glob(os.path.join(ROOT, "teachingflow-*.json")))
    if not keys:
        sys.exit("서비스 계정 키(teachingflow-*.json)를 저장소 루트에서 못 찾았습니다.")
    creds = service_account.Credentials.from_service_account_file(keys[0], scopes=SCOPES)
    return build("searchconsole", "v1", credentials=creds, cache_discovery=False)


def query(svc, days: int, dimensions: list[str], limit: int = 500,
          site: str = SITE) -> list[dict]:
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dimensions,
        "rowLimit": limit,
    }
    resp = svc.searchanalytics().query(siteUrl=site, body=body).execute()
    rows = []
    for r in resp.get("rows", []):
        rec = dict(zip(dimensions, r["keys"]))
        rec.update(clicks=r["clicks"], impressions=r["impressions"],
                   ctr=r["ctr"], position=r["position"])
        rows.append(rec)
    return rows


def show(rows, cols, title, limit=40):
    print(f"\n══════ {title} ══════")
    if not rows:
        print("  (데이터 없음)")
        return
    head = "  " + "".join(f"{c[:14]:<16}" for c in cols[:-4]) + \
           f"{'클릭':>7}{'노출':>9}{'CTR':>8}{'순위':>7}"
    print(head)
    for r in rows[:limit]:
        left = "".join(f"{str(r[c])[:38]:<40}" for c in cols[:-4])
        print(f"  {left}{r['clicks']:>7}{r['impressions']:>9}"
              f"{r['ctr']*100:>7.1f}%{r['position']:>7.1f}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--report", default="all",
                    choices=["all", "queries", "pages", "ctr", "striking"])
    ap.add_argument("--site", default=SITE,
                    help="속성 URL. 도메인 속성이면 sc-domain:opsoai.com 형식")
    args = ap.parse_args()

    try:
        svc = client()
        svc.sites().list().execute()
    except Exception as e:
        print("Search Console 접근 실패:", str(e)[:220])
        print("\n스크립트 상단의 '사전 준비' 두 단계를 먼저 끝내야 합니다.")
        return 1

    if args.report in ("all", "queries"):
        rows = query(svc, args.days, ["query"])
        rows.sort(key=lambda r: -r["impressions"])
        show(rows, ["query", "clicks", "impressions", "ctr", "position"],
             f"노출 상위 검색어 (최근 {args.days}일)")

    if args.report in ("all", "pages"):
        rows = query(svc, args.days, ["page"])
        rows.sort(key=lambda r: -r["impressions"])
        for r in rows:
            r["page"] = r["page"].replace("https://www.opsoai.com/", "/")
        show(rows, ["page", "clicks", "impressions", "ctr", "position"],
             f"노출 상위 페이지 (최근 {args.days}일)")

    if args.report in ("all", "ctr"):
        # 노출은 충분한데 클릭이 안 나오는 쿼리 = 제목/설명만 고쳐도 회수되는 구간
        rows = [r for r in query(svc, args.days, ["query", "page"])
                if r["impressions"] >= 20 and r["ctr"] < 0.02]
        rows.sort(key=lambda r: -r["impressions"])
        for r in rows:
            r["page"] = r["page"].replace("https://www.opsoai.com/", "/")
        show(rows, ["query", "page", "clicks", "impressions", "ctr", "position"],
             "제목 리라이팅 후보 (노출 20+ / CTR 2% 미만)")

    if args.report in ("all", "striking"):
        # 11~30위 = 1페이지 문턱. 새 글보다 이쪽 보강이 회수가 빠르다.
        rows = [r for r in query(svc, args.days, ["query", "page"])
                if 10 < r["position"] <= 30 and r["impressions"] >= 10]
        rows.sort(key=lambda r: -r["impressions"])
        for r in rows:
            r["page"] = r["page"].replace("https://www.opsoai.com/", "/")
        show(rows, ["query", "page", "clicks", "impressions", "ctr", "position"],
             "1페이지 문턱 기회 (11~30위 / 노출 10+)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
