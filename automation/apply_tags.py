#!/usr/bin/env python3
"""_posts의 글에 통제 어휘 기반 태그를 부여한다.

Chirpy의 관련글 추천은 태그 교집합으로 동작하는데 대부분의 글에 통제 태그가 없어
사실상 꺼져 있는 상태였다. 이 스크립트가 그 구멍을 메운다.

    python automation/apply_tags.py            # 드라이런: 분포만 출력, 파일 미변경
    python automation/apply_tags.py --write    # 실제 프론트매터에 기록
    python automation/apply_tags.py --write --force   # 기존 태그도 덮어씀

기존에 손으로 단 태그는 기본적으로 보존한다(--force로만 덮어씀).
"""

from __future__ import annotations

import argparse
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tag_taxonomy import (  # noqa: E402
    CATEGORY_FALLBACK,
    DEFAULT_FALLBACK,
    DEMOTED,
    GENERIC_RATIO,
    MAX_TAGS,
    MIN_TAGS,
    TAXONOMY,
    TITLE_WEIGHT,
)

POSTS_GLOB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_posts", "*.md")

# 본문 매칭 전에 걷어낼 것들. 코드블록, URL, 이미지 경로에 걸리는 오탐이 상당히 많다.
_CODE_FENCE = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_URL = re.compile(r"https?://\S+")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_HTML_TAG = re.compile(r"</?[A-Za-z][^>\n]*>")
_INTERNAL_LINK_BLOCK = re.compile(
    r"<!-- internal-links:start -->.*?<!-- internal-links:end -->", re.S
)
_PRIMARY_SOURCE_BLOCK = re.compile(
    r"<!-- primary-sources:start -->.*?<!-- primary-sources:end -->", re.S
)

# 본문 언급 점수의 상한. 제목 매칭(TITLE_WEIGHT)을 넘지 않게 잡아,
# 본문에서 100번 언급돼도 제목에 박힌 주제를 이기지 못하게 한다.
BODY_CAP = 6

# (태그, 컴파일된 패턴들, 제목전용 여부, 최소점수)로 정규화해 둔다.
_COMPILED = [
    (
        tag,
        [re.compile(p, re.I) for p in patterns],
        opts.get("title_only", False),
        opts.get("min", 1),
    )
    for tag, patterns, opts in TAXONOMY
]


def split_front_matter(text: str):
    """(front_matter, body, ok) 반환. 프론트매터가 없으면 ok=False."""
    if not text.startswith("---"):
        return "", text, False
    end = text.find("\n---", 3)
    if end == -1:
        return "", text, False
    return text[3:end], text[end + 4 :], True


def get_field(fm: str, name: str):
    m = re.search(rf"^{name}:\s*(.*)$", fm, re.M)
    return m.group(1).strip() if m else ""


def clean_title(raw: str) -> str:
    """따옴표와 날짜 접두사([2026-03-10] 같은)를 벗겨낸다."""
    t = raw.strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        t = t[1:-1]
    t = re.sub(r"^\[\d{4}-\d{2}-\d{2}\]\s*", "", t)
    return t


def strip_noise(body: str) -> str:
    body = _INTERNAL_LINK_BLOCK.sub(" ", body)
    body = _PRIMARY_SOURCE_BLOCK.sub(" ", body)
    body = _CODE_FENCE.sub(" ", body)
    body = _INLINE_CODE.sub(" ", body)
    body = _URL.sub(" ", body)
    body = _HTML_COMMENT.sub(" ", body)
    body = _HTML_TAG.sub(" ", body)
    return body


def has_tags(fm: str) -> bool:
    return bool(re.search(r"^tags:", fm, re.M))


def score_post(title: str, body: str) -> dict[str, int]:
    """태그별 점수. 제목 매칭에 TITLE_WEIGHT 배 가중치."""
    scores: dict[str, int] = {}
    # 본문은 앞부분에 주제가 몰려 있고 전문 스캔은 느리므로 앞 6000자만 본다.
    body_head = body[:6000]
    for tag, patterns, title_only, min_score in _COMPILED:
        s = 0
        # 제목 매칭은 몇 개 패턴이 걸리든 한 번만 센다. 같은 개념의 표기 변형
        # (nvidia / 엔비디아)이 동시에 걸려 점수가 부풀지 않게 하기 위함이다.
        if any(pat.search(title) for pat in patterns):
            s += TITLE_WEIGHT
        if not title_only:
            # 본문은 패턴별이 아니라 태그 단위로 합산 후 상한을 건다.
            # 패턴별 상한을 걸면 표기가 하나뿐인 태그가 min 점수에 영원히 못 닿는다.
            body_hits = sum(len(pat.findall(body_head)) for pat in patterns)
            s += min(body_hits, BODY_CAP)
        if s >= min_score:
            scores[tag] = s
    return scores


def tags_for(title: str, body: str, category: str = "") -> list[str]:
    """제목, 본문, 카테고리로 태그를 뽑는 단일 진입점. 자동 발행 봇이 호출한다.

    기존 코퍼스와 같은 통제 어휘와 같은 강등 기준을 쓰므로, 새 글이 옛 글과
    태그로 이어져 관련글 추천이 끊기지 않는다.
    """
    rec = {
        "scores": score_post(clean_title(title or ""), strip_noise(body or "")),
        "category": (category or "").strip().strip("\"'").lower(),
    }
    return pick_tags(rec, DEMOTED)


def collect(paths):
    """전 글을 훑어 점수를 모으고, 코퍼스 전체 매칭 빈도도 함께 센다."""
    records = []
    freq = collections.Counter()
    for path in paths:
        text = open(path, encoding="utf-8").read()
        fm, body, ok = split_front_matter(text)
        if not ok:
            continue
        title = clean_title(get_field(fm, "title"))
        category = get_field(fm, "categories").strip().strip("\"'").lower()
        scores = score_post(title, strip_noise(body))
        for tag in scores:
            freq[tag] += 1
        records.append(
            {
                "path": path,
                "text": text,
                "fm": fm,
                "title": title,
                "category": category,
                "scores": scores,
                "had_tags": has_tags(fm),
            }
        )
    return records, freq


def pick_tags(rec, generic: set[str]) -> list[str]:
    """점수 상위 MAX_TAGS개. 변별력 없는 태그는 뒤로 밀고, 부족하면 카테고리로 보충."""
    scores = rec["scores"]
    ranked = sorted(
        scores.items(),
        # 변별력 없는 태그(코퍼스 35% 초과 매칭)는 점수와 무관하게 후순위
        key=lambda kv: (kv[0] in generic, -kv[1], kv[0]),
    )
    tags = [t for t, _ in ranked[:MAX_TAGS]]

    if len(tags) < MIN_TAGS:
        for extra in CATEGORY_FALLBACK.get(rec["category"], []):
            if extra not in tags:
                tags.append(extra)
            if len(tags) >= MIN_TAGS:
                break
    if len(tags) < MIN_TAGS:
        for extra in DEFAULT_FALLBACK:
            if extra not in tags:
                tags.append(extra)
            if len(tags) >= MIN_TAGS:
                break
    if not tags:
        # 어느 패턴에도 안 걸린 글. 태그가 0개면 관련글에서 완전히 고립된다.
        tags = ["AI트렌드"]
    return tags[:MAX_TAGS]


def render_tags_block(tags: list[str]) -> str:
    return "tags:\n" + "".join(f"  - {t}\n" for t in tags)


def write_tags(text: str, fm: str, tags: list[str]) -> str:
    """프론트매터에 tags 블록을 주입(또는 교체)한다."""
    block = render_tags_block(tags)
    existing = re.search(r"^tags:[^\n]*(?:\n[ \t]*-[^\n]*)*", fm, re.M)
    if existing:
        new_fm = fm[: existing.start()] + block.rstrip("\n") + fm[existing.end() :]
    else:
        # categories 바로 뒤에 붙여 관련 필드끼리 모아둔다.
        cat = re.search(r"^categories:.*$", fm, re.M)
        if cat:
            new_fm = fm[: cat.end()] + "\n" + block.rstrip("\n") + fm[cat.end() :]
        else:
            new_fm = fm.rstrip("\n") + "\n" + block.rstrip("\n")
    _, body, _ = split_front_matter(text)
    return "---" + new_fm + "\n---" + body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="실제 파일에 기록")
    ap.add_argument("--force", action="store_true", help="기존 태그도 덮어씀")
    ap.add_argument("--show", type=int, default=12, help="샘플 출력 개수")
    args = ap.parse_args()

    paths = sorted(glob.glob(POSTS_GLOB))
    records, freq = collect(paths)
    total = len(records)

    generic = {t for t, c in freq.items() if c > total * GENERIC_RATIO}

    assigned = collections.Counter()
    per_post_counts = collections.Counter()
    changes = []
    for rec in records:
        if rec["had_tags"] and not args.force:
            continue
        tags = pick_tags(rec, generic)
        per_post_counts[len(tags)] += 1
        for t in tags:
            assigned[t] += 1
        changes.append((rec, tags))

    print(f"대상 글: {total}편 / 태그 부여 대상: {len(changes)}편")
    if generic:
        print(f"\n변별력 미달로 후순위 강등({int(GENERIC_RATIO*100)}% 초과 매칭): "
              + ", ".join(sorted(generic)))

    print("\n=== 글당 태그 수 분포 ===")
    for n in sorted(per_post_counts):
        print(f"  {n}개: {per_post_counts[n]}편")

    print(f"\n=== 부여된 태그 분포 (총 {len(assigned)}종) ===")
    for tag, cnt in assigned.most_common():
        bar = "█" * max(1, round(cnt / max(assigned.values()) * 36))
        print(f"  {tag:20} {cnt:4}  {bar}")

    unused = [t for t, _, _ in TAXONOMY if t not in assigned]
    if unused:
        print(f"\n한 번도 안 쓰인 태그({len(unused)}종): " + ", ".join(unused))

    print(f"\n=== 샘플 {args.show}편 ===")
    step = max(1, len(changes) // args.show)
    for rec, tags in changes[::step][: args.show]:
        print(f"  {os.path.basename(rec['path'])[:52]:54} → {', '.join(tags)}")

    if not args.write:
        print("\n[드라이런] 파일은 변경하지 않았습니다. 적용하려면 --write")
        return 0

    for rec, tags in changes:
        new_text = write_tags(rec["text"], rec["fm"], tags)
        with open(rec["path"], "w", encoding="utf-8") as f:
            f.write(new_text)
    print(f"\n[완료] {len(changes)}편에 태그를 기록했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
