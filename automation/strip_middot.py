#!/usr/bin/env python3
"""가운뎃점(U+00B7)을 문맥에 맞는 표기로 바꾼다.

표기 규칙상 가운뎃점은 어디에도 쓰지 않는다. 다만 일괄 치환하면 문장이 깨지는
자리가 있어서, 쓰임에 따라 다르게 바꾼다.

  "AI · 데이터"        나열      -> "AI, 데이터"
  "개발자·연구자"       두 항 나열 -> "개발자와 연구자"
  "설치 · 설정 · 배포"  세 항 이상 -> "설치, 설정, 배포"
  "2026 · 08"          숫자 구분  -> "2026-08"

코드 펜스 안(명령어, 출력 예시)은 건드리지 않는다. 실행 결과를 그대로 옮긴
곳이라 임의로 바꾸면 사실과 달라진다.

    python automation/strip_middot.py           # 드라이런
    python automation/strip_middot.py --write   # 적용
"""

from __future__ import annotations

import argparse
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIDDOT = "·"

TARGETS = [
    "_posts/*.md", "_tabs/*.md", "automation/*.py", "automation/*.md",
    "automation/*.json", "*.md", "*.txt", "_includes/*.html", "_layouts/*.html",
]

# mermaid와 chartjs 펜스는 보호 대상이 아니다. 코드가 아니라 화면에 그려지는
# 텍스트라서, 그 안의 가운뎃점은 독자 눈에 그대로 보인다.
_FENCE = re.compile(r"```(?!\s*(?:mermaid|chartjs)\b).*?```", re.S)
# 수식은 가운뎃점이 연산 기호다. $$G(·,·)$$ 를 "G(,)"로 바꾸면 내용이 틀려진다.
_MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$", re.S)
# script와 style 블록은 코드다. 정규식 문자 클래스 안의 가운뎃점을 바꾸면
# 매칭 동작이 달라진다. 실제로 _layouts/post.html 의 /[^\s|·]/ 가 훼손됐다.
_CODE_TAG = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)

# 받침이 있으면 "과", 없으면 "와". 한글 음절의 종성 유무로 판정한다.
def _josa_gwa(word: str) -> str:
    for ch in reversed(word):
        if "가" <= ch <= "힣":
            return "과" if (ord(ch) - 0xAC00) % 28 else "와"
        if ch.isalnum():
            return "와"
    return "와"


def convert(text: str) -> str:
    """가운뎃점 한 개를 문맥에 맞게 치환한다."""
    # 1) 숫자 사이: 2026 · 08 -> 2026-08
    text = re.sub(rf"(\d)\s*{MIDDOT}\s*(\d)", r"\1-\2", text)

    # 2) 세 항 이상 나열은 전부 쉼표로. 먼저 긴 사슬부터 처리한다.
    def chain(m):
        parts = [p.strip() for p in m.group(0).split(MIDDOT)]
        return ", ".join(parts)

    text = re.sub(
        rf"[^\s,()\[\]{MIDDOT}]+(?:\s*{MIDDOT}\s*[^\s,()\[\]{MIDDOT}]+){{2,}}",
        chain, text)

    # 3) 두 항 나열은 "과/와"로 이어 붙인다.
    def pair(m):
        left, right = m.group(1).strip(), m.group(2).strip()
        return f"{left}{_josa_gwa(left)} {right}"

    text = re.sub(
        rf"([^\s,()\[\]{MIDDOT}]+)\s*{MIDDOT}\s*([^\s,()\[\]{MIDDOT}]+)",
        pair, text)

    # 4) 남은 것(구분자 용도로 홀로 쓰인 경우)은 쉼표로.
    text = re.sub(rf"\s*{MIDDOT}\s*", ", ", text)
    return text


def process(text: str) -> str:
    """코드 펜스와 수식, 고유명사는 보존하고 나머지만 변환한다."""
    # 보존 대상을 자리표시자로 빼둔 뒤 변환하고 되돌린다.
    kept: list[str] = []

    def stash(m):
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"

    # 제품명은 조사로 이으면 안 된다. 널리 쓰이는 하이픈 표기로 먼저 바꿔 둔다.
    text = re.sub(r"DALL\u00b7E", "DALL-E", text)

    guarded = _FENCE.sub(stash, text)
    guarded = _CODE_TAG.sub(stash, guarded)
    guarded = _MATH.sub(stash, guarded)

    converted = convert(guarded)
    return re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], converted)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", type=int, default=10)
    args = ap.parse_args()

    edits, total = [], 0
    seen = set()
    for pattern in TARGETS:
        for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
            if path in seen or os.path.basename(path) == "strip_middot.py":
                continue
            seen.add(path)
            try:
                text = open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, IsADirectoryError):
                continue
            if MIDDOT not in text:
                continue
            new = process(text)
            n = text.count(MIDDOT) - new.count(MIDDOT)
            if n:
                total += n
                edits.append((path, new, n, text))

    print(f"대상 {len(edits)}개 파일 / 가운뎃점 {total}개\n")
    for path, new, n, old in edits[: args.show]:
        rel = os.path.relpath(path, ROOT)
        print(f"▶ {rel}  ({n}개)")
        for om, nm in zip(re.finditer(rf".{{0,34}}{MIDDOT}.{{0,34}}", old),
                          range(2)):
            snippet = om.group(0).replace("\n", " ")
            print(f"    before: …{snippet}…")
        print()
    if len(edits) > args.show:
        print(f"… 외 {len(edits) - args.show}개 파일\n")

    if not args.write:
        print("[드라이런] 적용하려면 --write")
        return 0

    for path, new, _, _ in edits:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
    print(f"[완료] {len(edits)}개 파일에서 {total}개 제거")

    left = []
    for path in seen:
        try:
            if MIDDOT in open(path, encoding="utf-8").read():
                left.append(os.path.relpath(path, ROOT))
        except Exception:
            pass
    print("남은 가운뎃점:", "없음" if not left else f"{len(left)}개 파일 (코드 펜스 내부) {left[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
