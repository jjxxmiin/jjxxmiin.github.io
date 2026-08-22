#!/usr/bin/env python3
"""구글과 네이버 자동완성에서 실제 검색어를 수집해 키워드 뱅크를 만든다.

키워드를 상상해서 적으면 검색 수요가 없는 글을 또 612편 쓰게 된다.
자동완성은 실제로 사람들이 친 질의에서 나오므로, 적어도 '아무도 안 찾는 말'은
아니라는 보증이 된다. 절대 검색량은 알 수 없지만 상대 우선순위는 잡을 수 있다.

수집 방식
    시드 → 자동완성 → (선택) 그 결과를 다시 시드로 1단계 더 확장
    두 엔진 모두에서 나온 질의, 여러 시드에서 겹쳐 나온 질의에 가산점을 준다.

    python automation/harvest_keywords.py --out keywords.json
    python automation/harvest_keywords.py --depth 2 --out keywords.json
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; OPSOAI-keyword-research/1.0)"
DELAY = 0.35  # 자동완성은 공개 엔드포인트다. 예의상 간격을 둔다.

# ─────────────────────────── 시드 ───────────────────────────
# 링별로 나눠 둔다. 나중에 어느 링이 수요가 큰지 비교할 수 있어야 한다.
SEEDS = {
    "ring1_직장인": [
        "챗gpt로 보고서", "챗gpt 엑셀", "AI 회의록", "AI ppt 만들기",
        "AI 문서 요약", "챗gpt 업무 활용", "AI 업무 자동화", "AI 메일 작성",
        "클로드 사용법", "노션 AI 사용법", "AI 데이터 분석", "AI 번역",
        "챗gpt 프롬프트", "제미나이 사용법", "AI 기획서",
    ],
    "ring2_사업자": [
        "AI 상세페이지", "AI 썸네일 만들기", "AI 블로그 글쓰기", "AI 광고 문구",
        "AI 로고 만들기", "AI 영상 편집", "AI 자막", "AI 쇼츠 만들기",
        "AI 인스타 게시물", "챗gpt 마케팅", "AI 고객 응대",
    ],
    "ring3_학생취준": [
        "AI 자소서", "챗gpt 자소서", "AI 과제", "AI 논문 요약",
        "AI 공부법", "AI 영어 공부", "챗gpt 면접",
    ],
    "고단가_상업의도": [
        "AI 강의", "AI 자격증", "챗gpt 요금제", "클로드 요금제",
        "AI 도구 추천", "AI 무료", "챗gpt 유료 차이", "AI 교육",
    ],
    "ring0_개발자": [
        "클로드 코드", "MCP 서버", "AI 코딩", "로컬 LLM", "RAG 구축",
    ],
}

# 접미 확장에 쓸 글자. 한글 초성/자주 오는 조사와 의문사 + 알파벳 일부.
EXPANSIONS = list("가나다라마바사아자차카타파하") + [
    "방법", "무료", "추천", "비교", "가격", "오류", "안됨", "사용법", "차이",
]

# 상업적/실행 의도 신호. 애드센스 단가와 강의 전환 양쪽에 유리한 쿼리를 골라낸다.
INTENT = {
    "가격": 3, "요금": 3, "비용": 3, "결제": 3, "유료": 2, "무료": 2,
    "추천": 3, "비교": 3, "순위": 2, "차이": 2, "vs": 2,
    "강의": 3, "교육": 2, "자격증": 3, "배우기": 2, "학원": 3,
    "방법": 2, "사용법": 2, "만들기": 2, "하는법": 2, "설정": 1, "설치": 1,
    "오류": 2, "안됨": 2, "해결": 2, "에러": 2,
    "후기": 2, "리뷰": 1, "템플릿": 2, "프롬프트": 2,
}


def _get(url: str, headers: dict) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=10).read()


def google_suggest(q: str) -> list[str]:
    url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode(
        {"client": "firefox", "hl": "ko", "gl": "kr", "q": q}
    )
    try:
        data = json.loads(_get(url, {"User-Agent": UA}).decode("utf-8"))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception:
        return []


def naver_suggest(q: str) -> list[str]:
    url = "https://ac.search.naver.com/nx/ac?" + urllib.parse.urlencode(
        {"q": q, "st": "100", "r_format": "json", "r_enc": "UTF-8",
         "r_unicode": "0", "t_koreng": "1", "frm": "nv", "ans": "2"}
    )
    try:
        data = json.loads(_get(url, {"User-Agent": UA,
                                     "Referer": "https://search.naver.com/"}).decode("utf-8"))
    except Exception:
        return []
    out = []
    for group in data.get("items", []) or []:
        for item in group or []:
            if item and item[0]:
                out.append(item[0])
    return out


def normalize(q: str) -> str:
    q = re.sub(r"\s+", " ", q.strip().lower())
    # 표기 흔들림을 하나로 모은다. 'chatgpt/챗gpt/챗지피티'가 따로 집계되면 순위가 왜곡된다.
    for pat, rep in [
        (r"\bchat ?gpt\b", "챗gpt"), (r"챗지피티", "챗gpt"), (r"지피티", "gpt"),
        (r"\bclaude\b", "클로드"), (r"\bgemini\b", "제미나이"), (r"제미니", "제미나이"),
        (r"\bnotion ai\b", "노션ai"), (r"인공지능", "ai"),
    ]:
        q = re.sub(pat, rep, q)
    return re.sub(r"\s+", " ", q).strip()


def intent_score(q: str) -> tuple[int, list[str]]:
    hits = [w for w in INTENT if w in q]
    return sum(INTENT[w] for w in hits), hits


def classify(q: str) -> str:
    """기획서의 6개 포맷 중 어디에 해당하는 질의인지."""
    if any(w in q for w in ("가격", "요금", "비용", "유료", "무료", "결제")):
        return "③가격과 요금제"
    if any(w in q for w in ("추천", "비교", "vs", "순위", "차이")):
        return "②비교와 추천"
    if any(w in q for w in ("오류", "안됨", "에러", "해결", "실패")):
        return "④오류해결"
    if any(w in q for w in ("프롬프트", "템플릿", "예시", "모음")):
        return "⑤프롬프트와 템플릿"
    if any(w in q for w in ("방법", "사용법", "만들기", "하는법", "설치", "설정", "쓰는법", "활용")):
        return "①실전 사용법"
    return "기타"


def harvest(depth: int, verbose: bool) -> dict:
    # key -> {engines, seeds, rings}
    found: dict[str, dict] = collections.defaultdict(
        lambda: {"engines": set(), "seeds": set(), "rings": set()}
    )
    queue = [(ring, seed, 0) for ring, seeds in SEEDS.items() for seed in seeds]
    seen_queries = set()
    n_req = 0

    while queue:
        ring, q, level = queue.pop(0)
        variants = [q] if level > 0 else [q] + [f"{q} {e}" for e in EXPANSIONS]
        for v in variants:
            if v in seen_queries:
                continue
            seen_queries.add(v)
            for engine, fn in (("google", google_suggest), ("naver", naver_suggest)):
                for s in fn(v):
                    key = normalize(s)
                    if len(key) < 4 or len(key) > 40:
                        continue
                    rec = found[key]
                    rec["engines"].add(engine)
                    rec["seeds"].add(q)
                    rec["rings"].add(ring)
                n_req += 1
                time.sleep(DELAY)
            if verbose and n_req % 40 == 0:
                print(f"  요청 {n_req}건과 수집 {len(found)}개", file=sys.stderr)

        if level + 1 < depth:
            # 이번 시드에서 나온 상위 결과만 다시 확장한다. 전부 하면 폭발한다.
            children = [k for k, v in found.items() if q in v["seeds"]][:6]
            queue += [(ring, c, level + 1) for c in children]

    rows = []
    for kw, rec in found.items():
        score, hits = intent_score(kw)
        # 두 엔진 모두에서 나오면 +3, 여러 시드에서 겹치면 겹친 만큼 가산.
        both = 3 if len(rec["engines"]) == 2 else 0
        overlap = min(len(rec["seeds"]) - 1, 5)
        rows.append({
            "keyword": kw,
            "format": classify(kw),
            "rings": sorted(rec["rings"]),
            "engines": sorted(rec["engines"]),
            "intent_hits": hits,
            "score": score + both + overlap,
        })
    rows.sort(key=lambda r: (-r["score"], r["keyword"]))
    return {"total_requests": n_req, "keywords": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=int, default=1, help="1=시드만, 2=결과 재확장")
    ap.add_argument("--out", default="keyword_bank.json")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    result = harvest(args.depth, not args.quiet)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    rows = result["keywords"]
    print(f"\n요청 {result['total_requests']}건 → 키워드 {len(rows)}개 → {args.out}")
    by_fmt = collections.Counter(r["format"] for r in rows)
    print("\n포맷별 분포")
    for k, v in by_fmt.most_common():
        print(f"  {k:16} {v}")
    print("\n상위 25개")
    for r in rows[:25]:
        print(f"  {r['score']:3}  [{r['format']:12}] {r['keyword'][:38]:40} {','.join(r['rings'])[:28]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
