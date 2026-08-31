#!/usr/bin/env python3
"""키워드 뱅크를 '글 주제' 단위 발행 큐로 묶는다.

원시 키워드를 하나씩 글로 만들면 안 된다. '클로드 요금제 가격'과
'클로드 요금제 비교'는 사실상 같은 글이라, 따로 쓰면 서로 순위를 갉아먹는
자기잠식(keyword cannibalization)이 된다. 그래서 머리말이 같은 키워드를
하나의 주제로 묶고, 대표 키워드는 제목에, 나머지는 소제목으로 흡수한다.

    python automation/build_topic_queue.py            # 미리보기
    python automation/build_topic_queue.py --write    # data/topic_queue.json 갱신
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apply_tags import split_front_matter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, "automation", "data", "keyword_bank.json")
QUEUE = os.path.join(ROOT, "automation", "data", "topic_queue.json")
LEDGER = os.path.join(ROOT, "automation", "data", "written_topics.json")

# 이미 여러 편 써서 도메인 권위가 쌓인 주제. 여기에 상업 포맷을 씌우는 게 T1이다.
OWNED = ["클로드 코드", "클로드 요금제", "클로드", "mcp 서버", "로컬 llm",
         "ai 코딩", "rag 구축", "챗gpt 요금제", "챗gpt"]
EDU = ["강의", "교육", "자격증", "학원"]
COMMERCIAL = ["추천", "비교", "가격", "요금", "차이", "무료", "후기", "순위", "만들기", "사용법"]

# 주제로 삼기에 너무 막연한 머리말. 글 하나로 답이 안 나온다.
TOO_VAGUE = {"ai 무료", "무료 ai", "ai 도구", "ai 추천", "ai 사용", "ai 활용", "ai 프로그램"}

# 지금은 쓰지 않는 계열.
#
# '강의 추천', '자격증 종류' 같은 글은 검색 수요가 크지만(수집 1,788개 중 239개),
# 팔 강의가 확정되기 전에는 정직하게 쓰면 "무료 자료로 충분하다"는 결론이 나와
# 글의 값어치가 떨어진다. 실제로 한 편 써 보고 폐기했다(2026-08-23).
#
# 강의 상품이 정해지면 이 집합을 비워서 되살릴 것. 그때는 자기 강의를 기준점으로
# 놓고 비교할 수 있어 글이 성립한다.
EXCLUDED_INTENT = ("강의", "자격증", "교육", "학원", "수업", "부트캠프")

FORMAT_RULES = [
    (("가격", "요금", "비용", "유료", "무료", "결제", "해지"), "가격과 요금제"),
    (("추천", "비교", "순위", "차이", "vs"), "비교와 추천"),
    (("오류", "안됨", "에러", "해결", "실패"), "오류 해결"),
    (("프롬프트", "템플릿", "예시", "모음"), "프롬프트와 템플릿"),
    (("방법", "사용법", "만들기", "구축", "설치", "설정"), "실전 사용법"),
]

# CPC나 제휴 수익을 아는 척하지 않는다. 아래 점수는 실제 수익이 아니라 검색어가
# '무엇을 살지/구독할지/도입할지'에 얼마나 가까운지를 나타내는 편집용 대체 지표다.
PURCHASE_WORDS = (
    "추천", "비교", "가격", "요금", "비용", "유료", "무료", "차이",
    "후기", "순위", "할인", "결제", "환불", "해지", "사양", "그래픽 카드",
)
IMPLEMENT_WORDS = (
    "오류", "안됨", "에러", "해결", "설치", "구축", "만들기", "설정", "사용법",
)


def commercial_value(keyword: str) -> tuple[int, str]:
    """Return purchase-intent proxy score and a human-readable intent label."""
    if any(word in keyword for word in PURCHASE_WORDS):
        return 5, "구매·구독 판단"
    if any(word in keyword for word in IMPLEMENT_WORDS):
        return 3, "도입·문제 해결"
    if "프롬프트" in keyword or "예시" in keyword or "템플릿" in keyword:
        return 2, "저장·재방문"
    return 1, "정보 탐색"


def tier_of(keyword: str) -> str | None:
    owned = any(o in keyword for o in OWNED)
    edu = any(e in keyword for e in EDU)
    comm = any(c in keyword for c in COMMERCIAL)
    if owned and comm:
        return "T1"
    if edu:
        return "T2"
    if comm:
        return "T3"
    return None


def format_of(primary: str) -> str:
    """대표 키워드 하나로만 판정한다.

    클러스터 전체를 이어붙여 보면 어딘가에 '무료'가 하나만 있어도 전부
    '가격과 요금제'로 쏠린다. 실제로 'mcp 서버 만들기'가 그렇게 오분류됐다.
    """
    for needles, name in FORMAT_RULES:
        if any(n in primary for n in needles):
            return name
    return "실전 사용법"


def head_of(keyword: str) -> str:
    """머리말 두 토큰. 같은 머리말이면 한 글로 묶는다."""
    toks = keyword.split()
    return " ".join(toks[:2]) if len(toks) >= 2 else keyword


def existing_slugs() -> set[str]:
    out = set()
    for p in glob.glob(os.path.join(ROOT, "_posts", "*.md")):
        out.add(os.path.basename(p)[11:-3].lower())
    return out


def written_ids() -> dict:
    """이미 발행한 주제 원장.

    제목 부분일치로 판단하면 안 된다. '클로드 코드'가 제목에 든 글이 68편이라
    그 주제 전체가 작성 완료로 잘못 잡힌다. 봇이 발행할 때 여기에 기록한다.
    """
    if not os.path.exists(LEDGER):
        return {}
    return json.load(open(LEDGER, encoding="utf-8")).get("written", {})


def build() -> list[dict]:
    rows = json.load(open(BANK, encoding="utf-8"))["keywords"]
    clusters: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        t = tier_of(r["keyword"])
        if not t:
            continue
        head = head_of(r["keyword"])
        if head in TOO_VAGUE or len(head) < 4:
            continue
        clusters[head].append(dict(r, tier=t, both=len(r["engines"]) == 2))

    written = written_ids()
    topics = []
    for head, members in clusters.items():
        # 제외 계열 키워드만 걸러낸다. 클러스터를 통째로 버리면 아까운 경우가 있다.
        # 예: '클로드 코드'는 변형이 63개인 최대 클러스터인데, 대표가 '강의 추천'이라는
        # 이유로 버리면 '가격', '사용법' 같은 멀쩡한 변형까지 함께 사라진다.
        members = [m for m in members
                   if not any(x in m["keyword"] for x in EXCLUDED_INTENT)]
        # 변형이 3개 미만이면 글 한 편을 채울 만큼의 폭이 안 나온다.
        if len(members) < 3:
            continue
        members.sort(key=lambda r: (-r["both"], -r["score"]))
        both_n = sum(1 for m in members if m["both"])
        # 주제 등급은 소속 키워드 중 가장 높은 것을 따른다.
        tier = min((m["tier"] for m in members), key=lambda t: ("T1", "T2", "T3").index(t))
        kws = [m["keyword"] for m in members]
        value_score, value_intent = max(
            (commercial_value(keyword) for keyword in kws),
            key=lambda pair: pair[0],
        )
        topic_format = format_of(members[0]["keyword"])
        # 추천·순위 글은 직접 같은 조건으로 써 보지 않으면 얕은 제휴 목록이 된다.
        # 자동화는 사실 기반 가격/사용법까지만 발행하고, 비교·추천은 실험 대기열로 둔다.
        publication_mode = (
            "manual_test" if topic_format == "비교와 추천" else "auto_research"
        )
        topics.append({
            # 한글을 지우면 안 된다. [^a-z0-9] 로 치환하면 한글 머리말이 전부
            # 빈 문자열이 되어 모든 주제가 같은 id를 갖는다.
            "id": re.sub(r"\s+", "-", head).strip("-"),
            "head": head,
            "tier": tier,
            "format": topic_format,
            "primary": members[0]["keyword"],
            "keywords": kws[:14],
            "variants": len(members),
            "both_engine": both_n,
            "commercial_value": value_score,
            "reader_intent": value_intent,
            "publication_mode": publication_mode,
            # 정렬 점수: 양엔진 검증 수 > 구매/도입 근접도 > 변형 수 > 최고 점수.
            # 실제 RPM이나 전환율이 생기면 이 대체 점수 대신 그 데이터를 쓴다.
            "priority": (
                both_n * 10 + value_score * 5
                + min(len(members), 20) + members[0]["score"]
            ),
            "status": "pending",
        })

    # 원장에 있는 주제만 done 으로 표시한다.
    for t in topics:
        if t["id"] in written:
            t["status"] = "done"
            t["post"] = written[t["id"]]

    order = {"T1": 0, "T2": 1, "T3": 2}
    topics.sort(key=lambda t: (order[t["tier"]], -t["priority"]))
    return topics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", type=int, default=18)
    args = ap.parse_args()

    topics = build()
    pending = [t for t in topics if t["status"] == "pending"]
    done = [t for t in topics if t["status"] == "done"]

    print(f"주제 {len(topics)}개 (대기 {len(pending)}, 작성됨 {len(done)})\n")
    by_tier = collections.Counter(t["tier"] for t in topics)
    print("등급별:", dict(by_tier), "\n")
    print(f"{'등급':<5}{'포맷':<12}{'가치':>4}{'변형':>4}{'양엔진':>6}  대표 키워드")
    for t in topics[: args.show]:
        mark = "  " if t["status"] == "pending" else "✓ "
        print(
            f"{mark}{t['tier']:<4}{t['format']:<12}{t['commercial_value']:>4}"
            f"{t['variants']:>4}{t['both_engine']:>6}  {t['primary'][:40]}"
        )
    if done:
        print(f"\n작성됨으로 표시된 주제: {', '.join(t['head'] for t in done)}")

    if not args.write:
        print("\n[미리보기] 저장하려면 --write")
        return 0
    os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
    with open(QUEUE, "w", encoding="utf-8") as f:
        json.dump({"topics": topics}, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {os.path.relpath(QUEUE, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
