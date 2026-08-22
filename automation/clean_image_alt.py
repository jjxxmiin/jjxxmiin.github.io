#!/usr/bin/env python3
"""arXiv 캡션에서 긁혀 온 이미지 alt 텍스트를 사람이 읽을 수 있게 정리한다.

논문 리뷰 글의 그림 alt에 LaTeX 명령과 유니코드 수학 기호가 그대로 남아 있고,
HTML에서 긁는 과정에서 문장 사이 공백까지 사라져 있다. 예:

    Figure 2:LoRWeB Overview.We first encode𝐚{\\mathbf{a}}and𝐚′{\\mathbf{a}}^{\\prime}, ...

alt는 접근성 텍스트이자 검색 신호라 이대로 두면 둘 다 손해다. 게다가 '{{'가
들어가면 Jekyll이 Liquid 태그로 오인해 빌드 경고를 낸다.

    python automation/clean_image_alt.py          # 드라이런
    python automation/clean_image_alt.py --write  # 적용
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apply_tags import split_front_matter  # noqa: E402

POSTS_GLOB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_posts", "*.md")

# 마크다운 이미지의 alt 부분만 잡는다: ![alt](url)
# alt 안에 논문 인용 '[5]' 같은 대괄호가 섞여 있으므로 '](' 직전까지 비탐욕 매칭한다.
# [^\]]* 로 잡으면 첫 ']'에서 끊겨 뒷부분 오염이 그대로 남는다.
IMG = re.compile(r"(!\[)(.*?)(\]\()")

# LaTeX 흔적으로 볼 만한 신호. 하나라도 있으면 정리 대상.
DIRTY = re.compile(r"\\[a-zA-Z]+|\{\{|\}\}|\$|[𝐚-𝐳𝐀-𝐙ℰℬℳ𝒜-𝒵]|_\{|\^\{")

_SUBS = [
    (re.compile(r"\$[^$]*\$"), " "),                  # $...$ 인라인 수식
    (re.compile(r"\\[a-zA-Z]+\s*"), " "),             # \mathcal, \prime 등 명령
    (re.compile(r"[_^]\{[^{}]*\}"), " "),             # 첨자 _{b} ^{2}
    (re.compile(r"[_^][A-Za-z0-9]"), " "),            # 중괄호 없는 첨자
    (re.compile(r"[{}]"), " "),                       # 남은 중괄호
    (re.compile(r"[𝐚-𝐳𝐀-𝐙𝑎-𝑧𝐴-𝑍ℰℬℳ𝒜-𝒵ℛℒ∧∨⊕⊗≈≜]"), " "),  # 유니코드 수학 문자
]


def clean_alt(alt: str) -> str:
    text = alt
    for pattern, repl in _SUBS:
        text = pattern.sub(repl, text)
    # arXiv HTML에서 긁으면 문장 경계 공백이 사라진다: "Overview.We first" -> "Overview. We first"
    # 문장부호 뒤에서만 띄운다. 소문자-대문자 경계까지 건드리면 LoRWeB, 3DiMo,
    # LingBot-VA 같은 고유명사가 'Lo RWe B'로 쪼개져 원본보다 나빠진다.
    # e.g. / i.e. / et al. 은 마침표가 문장 끝이 아니므로 분리 대상에서 제외한다.
    text = re.sub(r"\b(e|i)\.(g|e)\.", lambda m: f"{m.group(1)}\x00{m.group(2)}\x00", text)
    text = re.sub(r"([.,:;)\]])([A-Za-z])", r"\1 \2", text)
    text = text.replace("\x00", ".")
    text = re.sub(r"(Figure\s*\d+)\s*:\s*", r"\1: ", text)
    text = re.sub(r"\s+", " ", text).strip(" .,:;-")
    # alt는 짧아야 읽힌다. 문장 경계에서 끊는다.
    if len(text) > 125:
        cut = text[:125]
        dot = cut.rfind(". ")
        text = (cut[:dot] if dot > 40 else cut).rstrip(" .,:;-")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    edits = []
    for path in sorted(glob.glob(POSTS_GLOB)):
        text = open(path, encoding="utf-8").read()
        fm, body, ok = split_front_matter(text)
        if not ok:
            continue

        changed = []

        def repl(m):
            alt = m.group(2)
            if not DIRTY.search(alt):
                return m.group(0)
            new = clean_alt(alt)
            if not new or new == alt:
                return m.group(0)
            changed.append((alt, new))
            return m.group(1) + new + m.group(3)

        new_body = IMG.sub(repl, body)
        if changed:
            edits.append((path, "---" + fm + "\n---" + new_body, changed))

    for path, _, changed in edits:
        print(f"\n▶ {os.path.basename(path)[:64]}  ({len(changed)}건)")
        for old, new in changed[:2]:
            print(f"    before: {old[:105]}")
            print(f"    after : {new[:105]}")
    print(f"\n대상 {len(edits)}편 / 총 {sum(len(c) for _, _, c in edits)}건")

    if not args.write:
        print("[드라이런] 적용하려면 --write")
        return 0
    for path, content, _ in edits:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    print(f"[완료] {len(edits)}편 수정")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
