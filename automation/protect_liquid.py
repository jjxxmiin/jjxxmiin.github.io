#!/usr/bin/env python3
"""코드 예제 안의 {{ ... }} 를 Liquid이 먹어치우지 못하게 보호한다.

Jekyll은 코드 펜스 안이라도 Liquid을 먼저 처리한다. 그래서 GitHub Actions의
${{ secrets.FOO }} 나 Warp 워크플로우의 {{namespace}} 같은 플레이스홀더가
빈 문자열로 치환돼 렌더 결과에서 사라진다. 실제로 이런 코드가 나갔다.

    command: kubectl get pods -n  | grep CrashLoopBackOff     <- {{namespace}} 증발

예제의 핵심이 플레이스홀더인데 그게 사라지면 글이 틀린 정보가 된다.
{% raw %} ... {% endraw %} 로 감싸 원문 그대로 출력되게 한다.

    python automation/protect_liquid.py          # 드라이런
    python automation/protect_liquid.py --write  # 적용
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

# 여는 펜스부터 닫는 펜스까지. 백틱 수를 맞춰 잡아야 중첩 펜스에서 안 깨진다.
FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<ticks>`{3,})[^\n]*\n.*?^(?P=indent)(?P=ticks)[ \t]*$",
                   re.S | re.M)
# 이미 감싸 둔 구간. 이걸 먼저 걷어내지 않으면 재실행 때 이중으로 감싸게 된다.
RAW_BLOCK = re.compile(r"\{%-?\s*raw\s*-?%\}.*?\{%-?\s*endraw\s*-?%\}", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*\{\{[^`\n]*`")
LIQUID_VAR = re.compile(r"\{\{")


def protect(body: str) -> tuple[str, int]:
    """{{ 가 든 코드 펜스와 인라인 코드에 raw 태그를 씌운다. 여러 번 돌려도 안전하다."""
    count = 0

    # 이미 raw로 감싼 구간은 자리표시자로 빼두고 마지막에 되돌린다.
    already: list[str] = []

    def hide(m):
        already.append(m.group(0))
        return f"\x01{len(already) - 1}\x01"

    body = RAW_BLOCK.sub(hide, body)
    spans = []  # 펜스 구간을 기록해 두고, 그 바깥에서만 인라인 코드를 처리한다.

    def wrap_fence(m):
        nonlocal count
        block = m.group(0)
        if not LIQUID_VAR.search(block):
            return block
        if "{% raw %}" in block:
            return block
        count += 1
        indent = m.group("indent")
        return f"{indent}{{% raw %}}\n{block}\n{indent}{{% endraw %}}"

    # 먼저 펜스 위치를 기록
    for m in FENCE.finditer(body):
        spans.append((m.start(), m.end()))
    new_body = FENCE.sub(wrap_fence, body)

    # 펜스가 아닌 곳의 인라인 코드 처리. 펜스를 건드린 뒤라 위치가 밀리므로 다시 계산한다.
    protected_spans = [(m.start(), m.end()) for m in FENCE.finditer(new_body)]

    def in_fence(pos):
        return any(s <= pos < e for s, e in protected_spans)

    out = []
    last = 0
    for m in INLINE_CODE.finditer(new_body):
        if in_fence(m.start()):
            continue
        count += 1
        out.append(new_body[last:m.start()])
        out.append("{% raw %}" + m.group(0) + "{% endraw %}")
        last = m.end()
    out.append(new_body[last:])
    result = "".join(out)
    result = re.sub(r"\x01(\d+)\x01", lambda m: already[int(m.group(1))], result)
    return result, count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    edits = []
    for path in sorted(glob.glob(POSTS_GLOB)):
        text = open(path, encoding="utf-8").read()
        fm, body, ok = split_front_matter(text)
        if not ok or "{{" not in body:
            continue
        new_body, n = protect(body)
        if n:
            edits.append((path, "---" + fm + "\n---" + new_body, n))

    for path, _, n in edits:
        print(f"  {os.path.basename(path)[:66]:68} {n}곳 보호")
    print(f"\n대상 {len(edits)}편")

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
