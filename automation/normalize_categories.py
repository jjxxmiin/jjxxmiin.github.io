#!/usr/bin/env python3
"""_posts의 categories 값을 정규 집합으로 통일한다.

두 가지 문제를 고친다.

1) 대소문자 충돌: 'Tech'(304편)와 'tech'(165편)가 공존해 Jekyll이
   _site/categories/tech/index.html 을 두 번 쓰려다 빌드 경고를 낸다.
   Chirpy는 카테고리 URL을 소문자로 slugify하므로 병합해도 URL은 그대로다.

2) 1~6편짜리 자투리 카테고리: 거의 빈 아카이브 페이지가 양산돼
   thin content로 취급된다. 성격이 같은 것끼리 묶는다.

    python automation/normalize_categories.py          # 드라이런
    python automation/normalize_categories.py --write  # 적용
"""

from __future__ import annotations

import argparse
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apply_tags import get_field, split_front_matter  # noqa: E402

POSTS_GLOB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_posts", "*.md")

# 원본 값 -> 정규 값. 여기 없는 값은 그대로 둔다.
CANONICAL = {
    "tech": "Tech",
    "Tech": "Tech",
    "AI": "Tech",
    "mlops": "Tech",
    "money": "Tech",
    "paper": "Paper",
    "darknet": "DarkNet",
    "opensource": "OpenSource",
    # 2019~2022년 '끄적이기' 학습 노트 계열. 각각 2~6편이라 따로 두면
    # 아카이브 페이지가 사실상 비어 있게 된다.
    "python": "Basics",
    "concept": "Basics",
    "review": "Basics",
    "reinforcement": "Basics",
    "edge": "Basics",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    moves = collections.Counter()
    after = collections.Counter()
    edits = []

    for path in sorted(glob.glob(POSTS_GLOB)):
        text = open(path, encoding="utf-8").read()
        fm, _, ok = split_front_matter(text)
        if not ok:
            continue
        raw = get_field(fm, "categories")
        cur = raw.strip().strip("\"'")
        new = CANONICAL.get(cur, cur)
        after[new] += 1
        if new == cur and raw == cur:
            continue
        moves[f"{cur} → {new}"] += 1
        # categories 줄만 정확히 치환한다. 값에 따옴표나 후행 공백이 있어도 정리된다.
        new_fm = re.sub(r"^categories:.*$", f"categories: {new}", fm, count=1, flags=re.M)
        edits.append((path, "---" + new_fm + text[len("---") + len(fm) :]))

    print("=== 변경 내역 ===")
    for k, v in moves.most_common():
        print(f"  {v:4}  {k}")
    print("\n=== 정리 후 카테고리 ===")
    for k, v in after.most_common():
        print(f"  {v:4}  {k}")
    print(f"\n변경 대상 파일: {len(edits)}편")

    if not args.write:
        print("[드라이런] 적용하려면 --write")
        return 0

    for path, content in edits:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"[완료] {len(edits)}편 수정")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
