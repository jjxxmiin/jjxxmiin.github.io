#!/usr/bin/env python3
"""새로 발행된 글을 네이버와 Bing 에 즉시 색인 요청한다 (IndexNow).

크롤러가 사이트를 다시 방문할 때까지 기다리지 않고 "이 URL 이 새로 생겼다"를
검색엔진에 직접 알리는 프로토콜이다. 네이버는 2023년 7월부터 지원한다.

기본 동작은 직전 커밋에서 추가/수정된 _posts 파일을 URL 로 바꿔 제출하는 것이다.
URL 을 인자로 직접 넘길 수도 있다.

  python3 automation/ping_indexnow.py
  python3 automation/ping_indexnow.py https://www.opsoai.com/posts/foo/
  python3 automation/ping_indexnow.py --dry-run

인증은 루트에 올려 둔 키 파일(<key>.txt, 내용이 파일명과 같은 문자열)로 한다.
표준 라이브러리만 쓰므로 pip install 이 필요 없다.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "_posts")
TIMEOUT = 15

# 네이버와 Bing 각각의 수집 서버. 같은 프로토콜이라 본문(payload)은 동일하다.
ENDPOINTS = {
    "naver": "https://api.searchadvisor.naver.com/indexnow",
    "bing": "https://www.bing.com/indexnow",
}


def site_url():
    """_config.yml 의 url 을 그대로 쓴다. 하드코딩하면 도메인이 바뀔 때 조용히 틀어진다."""
    config = os.path.join(ROOT, "_config.yml")
    with open(config, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r'^url:\s*["\']?([^"\'\s#]+)', line)
            if match:
                return match.group(1).rstrip("/")
    raise SystemExit("_config.yml 에서 url 을 찾지 못했습니다.")


def find_key():
    """루트의 IndexNow 키 파일을 찾는다. 파일명(확장자 제외)과 내용이 같아야 유효하다."""
    override = os.environ.get("INDEXNOW_KEY", "").strip()
    if override:
        return override
    for name in sorted(os.listdir(ROOT)):
        if not name.endswith(".txt"):
            continue
        stem = name[:-4]
        if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", stem):
            continue
        try:
            with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
                if handle.read().strip() == stem:
                    return stem
        except OSError:
            continue
    raise SystemExit("루트에서 IndexNow 키 파일(<key>.txt)을 찾지 못했습니다.")


def slugify(name):
    """Jekyll 이 파일명에서 URL 을 만드는 규칙. 대소문자는 유지하고 구분자만 정리한다."""
    cleaned = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE)
    cleaned = re.sub(r"[\s.-]+", "-", cleaned)
    return cleaned.strip("-")


def _diff(base):
    return subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=d", base, "HEAD", "--", "_posts"],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=True,
    ).stdout


def changed_posts(base):
    """base 이후 추가되거나 수정된 글 파일. 삭제(d)는 색인 요청 대상이 아니다.

    base 는 보통 발행 워크플로가 돌기 시작한 커밋이라 정확히 새 글 한 건만 잡힌다.
    얕은 클론이라 그 커밋이 없거나 sha 가 비어 있으면 직전 커밋으로 물러선다."""
    for candidate in (base, "HEAD~1"):
        if not candidate:
            continue
        try:
            out = _diff(candidate)
        except (subprocess.SubprocessError, OSError) as exc:
            print(f"::warning::git diff {candidate} 실패 -> {exc}")
            continue
        return [line for line in out.splitlines() if line.endswith(".md")]
    return []


def post_url(path, base_url):
    basename = os.path.basename(path)[:-3]
    slug = slugify(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", basename))
    return f"{base_url}/posts/{urllib.parse.quote(slug)}/"


def is_live(url):
    """배포가 아직 안 끝난 URL 을 제출하면 엔진이 그냥 버린다. 살아 있는 것만 보낸다."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "opsoai-indexnow/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        print(f"  아직 응답 없음({exc.code}): {url}")
    except (urllib.error.URLError, OSError) as exc:
        print(f"  확인 실패({exc}): {url}")
    return False


def submit(engine, endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint, data=data, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "opsoai-indexnow/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            print(f"  {engine}: {response.status} {response.reason}")
            return True
    except urllib.error.HTTPError as exc:
        # 색인 요청이 실패해도 배포는 이미 끝났다. 경고만 남기고 파이프라인은 살린다.
        print(f"::warning::{engine} IndexNow 실패 {exc.code} -> {exc.read()[:200]!r}")
    except (urllib.error.URLError, OSError) as exc:
        print(f"::warning::{engine} IndexNow 요청 오류 -> {exc}")
    return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    base_url = site_url()
    host = urllib.parse.urlparse(base_url).netloc

    if args:
        urls = args
    else:
        base = os.environ.get("INDEXNOW_BASE", "").strip() or "HEAD~1"
        urls = [post_url(path, base_url) for path in changed_posts(base)]

    if not urls:
        print("색인 요청할 새 글이 없습니다.")
        return

    print(f"후보 {len(urls)}건")
    live = [url for url in urls if dry_run or is_live(url)]
    if not live:
        print("::warning::살아 있는 URL 이 없어 색인 요청을 건너뜁니다.")
        return

    key = find_key()
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"{base_url}/{key}.txt",
        "urlList": live,
    }
    for url in live:
        print(f"  제출: {url}")

    if dry_run:
        print("--dry-run: 실제 요청은 보내지 않았습니다.")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    for engine, endpoint in ENDPOINTS.items():
        submit(engine, endpoint, payload)


if __name__ == "__main__":
    main()
