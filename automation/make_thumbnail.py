#!/usr/bin/env python3
"""글마다 다른 대표 이미지(og:image)를 자동 생성한다.

지금 상태
  - 146편은 대표 이미지가 없어 사이트 기본 로고로 대체된다. 공유했을 때 전부 똑같이 보인다.
  - 477편은 외부 CDN(arXiv, 뉴스 원문)을 직접 건다. 브랜드가 없고, 원본이 내려가면 깨진다.

여기서 만드는 것
  1200x630(og:image 표준) 카드. 제목, 카테고리, 태그, 발행일을 얹고
  배경 색조는 슬러그 해시로 정해 글마다 다르게 나온다. 같은 글은 항상 같은 색이라
  다시 돌려도 git이 요동치지 않는다.

  headless Chromium으로 HTML을 찍는다. 한글은 Noto Sans CJK KR을 쓴다.

    python automation/make_thumbnail.py --missing        # 대표 이미지 없는 글 전부
    python automation/make_thumbnail.py _posts/2026-08-23-....md
    python automation/make_thumbnail.py --missing --write # 프론트매터까지 갱신
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apply_tags import clean_title, split_front_matter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_GLOB = os.path.join(ROOT, "_posts", "*.md")
OUT_DIR = os.path.join(ROOT, "assets", "img", "thumb")
REL_DIR = "/assets/img/thumb"

W, H = 1200, 630

# 카테고리별 기준 색조. 같은 카테고리는 계열이 비슷하게, 글마다는 조금씩 다르게 나온다.
CATEGORY_HUE = {
    "Tech": 168,        # 청록
    "Paper": 262,       # 보라
    "DarkNet": 20,      # 주황
    "OpenSource": 210,  # 파랑
    "Basics": 120,      # 초록
}


def find_chromium() -> str:
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("headless 렌더에 쓸 Chromium 계열 브라우저를 찾지 못했습니다.")


def palette(slug: str, category: str) -> dict:
    """슬러그에서 결정론적으로 색을 뽑는다. 같은 글은 언제 돌려도 같은 색."""
    h = int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16)
    base = CATEGORY_HUE.get(category, 168)
    # 카테고리 색조를 중심으로 좌우 30도 안에서만 흔든다. 계열은 유지하되 글마다 달라진다.
    hue = (base + (h % 61) - 30) % 360
    return {
        "h1": hue,
        "h2": (hue + 38) % 360,
        "angle": 115 + (h >> 8) % 50,
    }


def fit_title(title: str) -> tuple[str, int]:
    """길이에 따라 글자 크기를 낮춘다. 한글은 한 글자가 넓어 기준을 따로 잡는다."""
    n = len(title)
    if n <= 28:
        return title, 62
    if n <= 44:
        return title, 52
    if n <= 62:
        return title, 44
    return title[:78].rstrip() + "…", 38


def build_html(title: str, category: str, tags: list[str], date: str, slug: str) -> str:
    p = palette(slug, category)
    shown, size = fit_title(title)
    chips = "".join(
        f'<span class="chip">{html.escape(t)}</span>' for t in tags[:4]
    )
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    width:{W}px; height:{H}px; overflow:hidden;
    font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif;
    background:#0d1117; color:#fff;
    display:flex; flex-direction:column; justify-content:space-between;
    padding:64px 72px; position:relative;
  }}
  /* 배경: 카테고리 색조 기반 그라디언트 + 미세한 격자 */
  body::before {{
    content:""; position:absolute; inset:0;
    background:linear-gradient({p['angle']}deg,
      hsl({p['h1']} 62% 22%) 0%,
      hsl({p['h1']} 58% 13%) 48%,
      hsl({p['h2']} 55% 16%) 100%);
  }}
  body::after {{
    content:""; position:absolute; inset:0; opacity:.16;
    background-image:
      linear-gradient(hsl({p['h1']} 70% 62% / .5) 1px, transparent 1px),
      linear-gradient(90deg, hsl({p['h1']} 70% 62% / .5) 1px, transparent 1px);
    background-size:52px 52px;
    -webkit-mask-image:radial-gradient(ellipse 90% 70% at 82% 15%, #000 0%, transparent 72%);
  }}
  .row {{ position:relative; display:flex; align-items:center; gap:14px; }}
  .brand {{
    font-size:22px; font-weight:800; letter-spacing:.16em;
    color:hsl({p['h1']} 78% 72%);
  }}
  .cat {{
    font-size:16px; font-weight:600; padding:5px 13px; border-radius:5px;
    background:hsl({p['h1']} 60% 70% / .18);
    border:1px solid hsl({p['h1']} 60% 70% / .38);
    color:hsl({p['h1']} 70% 84%);
  }}
  .date {{ margin-left:auto; font-size:16px; color:#ffffff88; font-variant-numeric:tabular-nums; }}
  h1 {{
    position:relative; font-size:{size}px; font-weight:800; line-height:1.34;
    letter-spacing:-.02em; word-break:keep-all; max-width:20ch;
    text-shadow:0 2px 26px rgba(0,0,0,.4);
  }}
  .rule {{
    position:relative; width:76px; height:5px; border-radius:3px; margin-bottom:26px;
    background:hsl({p['h1']} 74% 60%);
  }}
  .chips {{ position:relative; display:flex; gap:9px; flex-wrap:wrap; }}
  .chip {{
    font-size:17px; font-weight:500; padding:7px 15px; border-radius:6px;
    background:#ffffff14; border:1px solid #ffffff2b; color:#ffffffd8;
  }}
</style></head><body>
  <div class="row">
    <span class="brand">OPSOAI</span>
    <span class="cat">{html.escape(category)}</span>
    <span class="date">{html.escape(date)}</span>
  </div>
  <div>
    <div class="rule"></div>
    <h1>{html.escape(shown)}</h1>
  </div>
  <div class="chips">{chips}</div>
</body></html>"""


def render(html_text: str, out_png: str, browser: str) -> None:
    # snap으로 설치된 Chromium은 confinement 때문에 /tmp 도, 홈의 숨김 디렉터리(.cache)도
    # 읽지 못한다. 각각 ERR_FILE_NOT_FOUND 와 ERR_ACCESS_DENIED 로 떨어진다.
    # 저장소 안의 숨김이 아닌 경로에 두면 통과한다.
    scratch = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumb_tmp")
    os.makedirs(scratch, exist_ok=True)
    # Chromium의 --screenshot 은 PNG만 낸다. 최종이 jpg면 일단 png로 받는다.
    shot_target = out_png[:-4] + ".png" if out_png.endswith(".jpg") else out_png
    with tempfile.TemporaryDirectory(dir=scratch) as tmp:
        src = os.path.join(tmp, "card.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(html_text)
        subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-sandbox",
             "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--window-size={W},{H}",
             f"--screenshot={shot_target}", f"file://{src}"],
            check=True, capture_output=True, timeout=90,
        )
    # 배경이 그라디언트라 PNG로 두면 200KB를 넘는다. 색 수 감축은 효과가 없어
    # (트루컬러로 다시 쓰임) JPEG로 변환한다. 같은 카드가 90KB 아래로 떨어진다.
    if out_png.endswith(".jpg") and shutil.which("convert"):
        tmp_png = shot_target
        subprocess.run(["convert", tmp_png, "-strip", "-quality", "84",
                        "-sampling-factor", "4:2:0", out_png],
                       check=True, capture_output=True)
        os.remove(tmp_png)


def generate_card(slug: str, title: str, category: str, tags: list[str],
                  date: str) -> str:
    """카드 한 장을 만들고 사이트 기준 상대 경로를 돌려준다.

    자동 발행 봇이 원문 이미지를 못 구했을 때 로고 대신 부르는 진입점이다.
    로고로 대체하면 모든 글의 공유 썸네일이 똑같아진다.
    """
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{slug}.jpg")
    if not os.path.exists(out):
        render(build_html(title, category, tags, date, slug), out, find_chromium())
    return f"{REL_DIR}/{slug}.jpg"


def post_meta(path: str):
    text = open(path, encoding="utf-8").read()
    fm, _, ok = split_front_matter(text)
    if not ok:
        return None
    data = yaml.safe_load(fm) or {}
    slug = os.path.basename(path)[11:-3]
    date = os.path.basename(path)[:10]
    return {
        "path": path, "text": text, "fm": fm, "data": data, "slug": slug,
        "title": clean_title(str(data.get("title", ""))),
        "category": str(data.get("categories", "Tech")).strip(),
        "tags": [str(t) for t in (data.get("tags") or [])],
        "date": date,
    }


def has_image(data: dict) -> bool:
    img = data.get("image")
    if isinstance(img, dict):
        return bool(img.get("path"))
    return bool(img)


def yaml_str(value: str) -> str:
    """YAML 스칼라로 안전하게 감싼다.

    제목에 콜론이 흔하다("MoAI 톺아보기: 차세대 모델"). 따옴표 없이 쓰면
    YAML이 두 번째 콜론을 매핑 구분자로 읽어 프론트매터 전체가 깨진다.
    """
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def set_image(text: str, fm: str, rel_path: str, alt: str) -> str:
    block = f"image:\n  path: {rel_path}\n  alt: {yaml_str(alt)}\n"
    existing = re.search(r"^image:\s*\n(?:[ \t]+\S.*\n)*", fm + "\n", re.M)
    if existing:
        new_fm = (fm + "\n").replace(existing.group(0), block, 1).rstrip("\n")
    else:
        anchor = re.search(r"^(?:summary|description|categories):.*$", fm, re.M)
        pos = anchor.end() if anchor else len(fm.rstrip("\n"))
        new_fm = fm[:pos] + "\n" + block.rstrip("\n") + fm[pos:]
    _, body, _ = split_front_matter(text)
    return "---" + new_fm + "\n---" + body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--missing", action="store_true", help="대표 이미지 없는 글 전부")
    ap.add_argument("--write", action="store_true", help="프론트매터에 경로 기록")
    ap.add_argument("--force", action="store_true", help="이미 있어도 다시 만듦")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    browser = find_chromium()
    os.makedirs(OUT_DIR, exist_ok=True)

    targets = []
    for path in (args.paths or (sorted(glob.glob(POSTS_GLOB)) if args.missing else [])):
        m = post_meta(path)
        if not m:
            continue
        if args.missing and has_image(m["data"]) and not args.force:
            continue
        targets.append(m)
    if args.limit:
        targets = targets[: args.limit]
    if not targets:
        print("대상이 없습니다. --missing 을 주거나 경로를 지정하세요.")
        return 0

    print(f"대상 {len(targets)}편\n")
    made = 0
    for m in targets:
        out = os.path.join(OUT_DIR, m["slug"] + ".jpg")
        rel = f"{REL_DIR}/{m['slug']}.jpg"
        if os.path.exists(out) and not args.force:
            print(f"  (있음) {m['slug'][:56]}")
        else:
            render(build_html(m["title"], m["category"], m["tags"], m["date"], m["slug"]),
                   out, browser)
            made += 1
            size = os.path.getsize(out) // 1024
            print(f"  생성  {m['slug'][:52]:54} {size}KB")
        if args.write:
            alt = f"{m['title'][:60]} 대표 이미지"
            with open(m["path"], "w", encoding="utf-8") as f:
                f.write(set_image(m["text"], m["fm"], rel, alt))

    print(f"\n새로 만든 이미지 {made}장 → {REL_DIR}/")
    if not args.write:
        print("프론트매터에 반영하려면 --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
