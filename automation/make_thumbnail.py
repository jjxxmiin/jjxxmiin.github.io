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

# 카테고리별 액센트. 채도를 낮춰 잡았다. 형광에 가까운 색은 싸 보인다.
# 카드에서 색이 들어가는 곳은 점 하나와 짧은 선 하나뿐이고 나머지는 전부 무채색이다.
CATEGORY_ACCENT = {
    "Tech":       (172, 42, 34),   # 딥 틸
    "Paper":      (258, 30, 42),   # 뮤티드 퍼플
    "DarkNet":    (14, 44, 42),    # 테라코타
    "OpenSource": (212, 38, 40),   # 슬레이트 블루
    "Basics":     (128, 30, 36),   # 세이지 그린
}

# 종이 느낌의 웜 오프화이트. 순백은 화면에서 눈이 부시고 싸구려로 보인다.
GROUND = "#FAF9F6"
INK = "#14151A"
MUTED = "#83858C"
HAIRLINE = "#E4E2DC"


def find_chromium() -> str:
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("headless 렌더에 쓸 Chromium 계열 브라우저를 찾지 못했습니다.")


def palette(slug: str, category: str) -> str:
    """카테고리 액센트를 슬러그로 아주 조금만 흔든다.

    ±10도 안에서만 움직인다. 글마다 다르되 한 벌로 보이게 하려는 것이다.
    색을 크게 돌리면 사이트 전체가 알록달록해져 프리미엄한 느낌이 사라진다.
    """
    h = int(hashlib.sha256(slug.encode()).hexdigest()[:8], 16)
    base_h, sat, light = CATEGORY_ACCENT.get(category, CATEGORY_ACCENT["Tech"])
    hue = (base_h + (h % 21) - 10) % 360
    return f"hsl({hue} {sat}% {light}%)"


def fit_title(title: str) -> tuple[str, int]:
    """길이에 따라 글자 크기를 낮춘다. 한글은 한 글자가 넓어 기준을 따로 잡는다."""
    n = len(title)
    if n <= 24:
        return title, 58
    if n <= 40:
        return title, 48
    if n <= 58:
        return title, 41
    return title[:74].rstrip() + "…", 35


def build_html(title: str, category: str, tags: list[str], date: str, slug: str) -> str:
    accent = palette(slug, category)
    shown, size = fit_title(title)
    # 태그는 알약 모양 칩 대신 담백한 텍스트로 늘어놓는다. 칩이 많아지면
    # 카드가 UI 스크린샷처럼 보이고 프리미엄한 느낌이 사라진다.
    meta = "  /  ".join(html.escape(t) for t in tags[:4])
    y, m, d = date.split("-")
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    width:{W}px; height:{H}px; overflow:hidden;
    background:{GROUND}; color:{INK};
    font-family:"Pretendard","Pretendard Variable","Noto Sans CJK KR",sans-serif;
    font-feature-settings:"ss01";
    display:flex; flex-direction:column;
    padding:76px 84px 72px;
  }}
  /* 카드 안쪽 실선 하나. 여백을 규정해 주는 최소한의 장치다. */
  .frame {{
    position:absolute; inset:34px;
    border:1px solid {HAIRLINE};
    pointer-events:none;
  }}
  header {{ display:flex; align-items:center; gap:12px; }}
  .dot {{ width:9px; height:9px; border-radius:50%; background:{accent}; flex:none; }}
  .brand {{
    font-size:15px; font-weight:700; letter-spacing:.22em;
    color:{INK};
  }}
  .cat {{
    font-size:13px; font-weight:500; letter-spacing:.08em;
    color:{MUTED};
  }}
  .date {{
    margin-left:auto; font-size:13px; color:{MUTED};
    font-variant-numeric:tabular-nums; letter-spacing:.04em;
  }}
  main {{ flex:1; display:flex; align-items:center; }}
  h1 {{
    font-size:{size}px; font-weight:700; line-height:1.38;
    letter-spacing:-.028em; word-break:keep-all;
    max-width:19ch; color:{INK};
  }}
  footer {{ display:flex; flex-direction:column; gap:16px; }}
  .rule {{ width:44px; height:2px; background:{accent}; }}
  .tags {{
    font-size:15px; color:{MUTED}; letter-spacing:.01em;
  }}
</style></head><body>
  <div class="frame"></div>
  <header>
    <span class="dot"></span>
    <span class="brand">OPSOAI</span>
    <span class="cat">{html.escape(category)}</span>
    <span class="date">{y}.{m}.{d}</span>
  </header>
  <main><h1>{html.escape(shown)}</h1></main>
  <footer>
    <div class="rule"></div>
    <div class="tags">{meta}</div>
  </footer>
</body></html>"""


def render(html_text: str, out_png: str, browser: str) -> None:
    # snap으로 설치된 Chromium은 confinement 때문에 /tmp 도, 홈의 숨김 디렉터리(.cache)도
    # 읽지 못한다. 각각 ERR_FILE_NOT_FOUND 와 ERR_ACCESS_DENIED 로 떨어진다.
    # 저장소 안의 숨김이 아닌 경로에 두면 통과한다.
    scratch = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumb_tmp")
    os.makedirs(scratch, exist_ok=True)
    # 렌더가 중간에 끊기면 임시 디렉터리가 남는다. 시작할 때 한 번 걷어낸다.
    for stale in os.listdir(scratch):
        stale_path = os.path.join(scratch, stale)
        if os.path.isdir(stale_path):
            shutil.rmtree(stale_path, ignore_errors=True)
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
             "--virtual-time-budget=4000",  # 웹폰트(Pretendard) 로드 대기
             f"--screenshot={shot_target}", f"file://{src}"],
            check=True, capture_output=True, timeout=90,
        )
    if not os.path.exists(shot_target):
        raise RuntimeError(f"브라우저가 스크린샷을 만들지 못했습니다: {shot_target}")

    # PNG로 두면 장당 200KB를 넘는다. JPEG로 바꿔 4분의 1로 줄인다.
    # ImageMagick 이 없는 환경(CI에서 apt 설치가 실패한 경우 등)에서는
    # 변환을 건너뛰고 PNG를 그대로 쓴다. 여기서 조용히 넘어가면
    # 존재하지 않는 .jpg 경로가 프론트매터에 박혀 이미지가 통째로 깨진다.
    if out_png.endswith(".jpg"):
        if shutil.which("convert"):
            subprocess.run(["convert", shot_target, "-strip", "-quality", "84",
                            "-sampling-factor", "4:2:0", out_png],
                           check=True, capture_output=True)
            os.remove(shot_target)
        else:
            print("  ImageMagick 이 없어 PNG로 저장합니다.")
            os.replace(shot_target, out_png)  # 확장자만 jpg, 내용은 png
            # 브라우저와 Jekyll 모두 내용 기반으로 처리하므로 표시에는 문제가 없다.


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
        # --force 는 '이미 있는 이미지 파일을 다시 그린다'는 뜻이지
        # '대표 이미지가 이미 있는 글까지 대상에 넣는다'는 뜻이 아니다.
        # 둘을 섞으면 외부 CDN 이미지를 쓰는 글까지 카드를 만들어
        # 아무도 참조하지 않는 파일이 수백 장 쌓인다.
        if args.missing and has_image(m["data"]):
            path = m["data"].get("image")
            path = path.get("path") if isinstance(path, dict) else path
            is_own_card = "/thumb/" in str(path or "")
            if not (is_own_card and args.force):
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
