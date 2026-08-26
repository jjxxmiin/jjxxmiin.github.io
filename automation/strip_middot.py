#!/usr/bin/env python3
"""가운뎃점(U+00B7)을 문맥에 맞는 표기로 바꾼다.

표기 규칙상 가운뎃점은 어디에도 쓰지 않는다. 다만 일괄 치환하면 문장이 깨지는
자리가 있어서, 쓰임에 따라 다르게 바꾼다.

  "AI · 데이터"        나열      -> "AI, 데이터"
  "개발자·연구자"       두 항 나열 -> "개발자, 연구자"
  "설치 · 설정 · 배포"  세 항 이상 -> "설치, 설정, 배포"
  "1·2·4·5"           숫자 나열 -> "1, 2, 4, 5"

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
    "_posts/*.md", "_tabs/*.md", "automation/*.md", "automation/*.json",
    "automation/data/*.json", "*.md", "*.txt", "_config.yml",
    "_includes/*.html", "_layouts/*.html", "assets/*.xml",
]

# mermaid와 chartjs 펜스는 화면에 그려지는 텍스트를 포함하므로 내용도 바꾼다.
# 일반 코드 펜스는 줄 단위 스캐너로 정확히 보호한다. 비탐욕 정규식은 앞 블록의
# 닫는 펜스를 다음 visual 블록의 여는 펜스로 오인해 중간 산문까지 숨길 수 있다.
_FENCE_OPEN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})([^\r\n]*)")
# 수식의 가운뎃점은 나열 기호가 아니라 연산자이므로 LaTeX 곱셈 기호로 바꾼다.
_MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$", re.S)
# script와 style 블록은 코드다. 정규식 문자 클래스 안의 가운뎃점을 바꾸면
# 매칭 동작이 달라진다. 실제로 _layouts/post.html 의 /[^\s|·]/ 가 훼손됐다.
_CODE_TAG = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)
# 인라인 코드는 짧더라도 식별자나 실제 명령일 수 있다. 산문과 분리해 원문을
# 보존한다. 펜스를 먼저 보호하므로 여기서는 한 줄짜리 backtick만 다룬다.
_INLINE_CODE = re.compile(r"`[^`\n]+`")
_SPECIAL_REPLACEMENTS = {
    "DALL·E": "DALL-E",
    "③가격·요금제": "③가격과 요금제",
    "②비교·추천": "②비교와 추천",
    "⑤프롬프트·템플릿": "⑤프롬프트와 템플릿",
}


def _guard_fences(text: str, stash_value) -> str:
    """일반 코드 펜스는 보존하고 visual 펜스의 독자 노출 문구만 변환한다."""
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    index = 0
    while index < len(lines):
        opening = _FENCE_OPEN.match(lines[index])
        if not opening:
            output.append(lines[index])
            index += 1
            continue

        marker = opening.group(1)
        language_text = opening.group(2).strip()
        language = language_text.split(None, 1)[0].casefold() if language_text else ""
        block = [lines[index]]
        index += 1
        closing = re.compile(
            rf"^[ \t]{{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*(?:\r?\n)?$"
        )
        while index < len(lines):
            block.append(lines[index])
            index += 1
            if closing.match(block[-1]):
                break
        value = "".join(block)
        if language in {"mermaid", "chartjs"}:
            output.append(convert(value))
        else:
            output.append(stash_value(value))
    return "".join(output)

def convert(text: str) -> str:
    """추측성 조사를 붙이지 않고 나열은 쉼표, 기호 연산은 곱셈표로 바꾼다."""
    for old, new in _SPECIAL_REPLACEMENTS.items():
        text = text.replace(old, new)
    # LaTeX 밖에 노출된 수식 중에서도 미분/거듭제곱 표지가 명시된 경우만
    # 곱셈으로 본다. 단순 x·y, p50·p95는 좌표나 지표 나열일 수 있으므로
    # 절대로 이 규칙에 포함하지 않는다.
    text = re.sub(
        rf"(?<![A-Za-z0-9])([A-Za-z])\s*{MIDDOT}\s*"
        rf"([A-Za-z](?:'\([^()\n]*\)|\^[A-Za-z0-9{{}}*+\-]+))",
        r"\1 × \2",
        text,
    )
    text = re.sub(
        rf"(?<![A-Za-z0-9])([A-Za-z]\([^()\n]*\))\s*{MIDDOT}\s*"
        rf"([A-Za-z]\([^()\n]*\))",
        r"\1 × \2",
        text,
    )
    # 그 밖은 명사 나열이다. 두 항에도 조사를 추측해 붙이지 않아 영문 혼용과
    # 전문 용어를 훼손하지 않는다.
    text = re.sub(rf"\s*{MIDDOT}\s*", ", ", text)
    return text


def process(text: str) -> str:
    """코드 펜스와 수식, 고유명사는 보존하고 나머지만 변환한다."""
    # 보존 대상을 자리표시자로 빼둔 뒤 변환하고 되돌린다.
    kept: list[str] = []

    def stash_value(value: str) -> str:
        kept.append(value)
        return f"\x00{len(kept) - 1}\x00"

    def stash(m):
        return stash_value(m.group(0))

    guarded = _guard_fences(text, stash_value)
    guarded = _CODE_TAG.sub(stash, guarded)
    guarded = _INLINE_CODE.sub(stash, guarded)

    def math_operator(m):
        value = re.sub(
            rf"(?<=[(,|])\s*{MIDDOT}\s*(?=[),|])",
            lambda _: r"\square",
            m.group(0),
        )
        return value.replace(MIDDOT, r"\times ")

    guarded = _MATH.sub(math_operator, guarded)

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
