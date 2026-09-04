#!/usr/bin/env python3
"""변경된 글을 네이버와 Bing 에 즉시 색인 요청한다 (IndexNow).

크롤러가 사이트를 다시 방문할 때까지 기다리지 않고 "이 URL 이 새로 생겼다"를
검색엔진에 직접 알리는 프로토콜이다. 네이버는 2023년 7월부터 지원한다.

기본 동작은 직전 커밋에서 추가/수정된 _posts 파일을 URL 로 바꿔 제출하는 것이다.
전역 SEO 템플릿이 바뀌면 배포된 sitemap 의 canonical URL 을 최대 10,000개까지
한 번에 제출한다. URL 을 인자로 직접 넘길 수도 있다.

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
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "_posts")
TIMEOUT = 15
MAX_URLS = 10_000
MAX_SITEMAP_BYTES = 20 * 1024 * 1024

# 이 파일들은 한 번 바뀌면 많은 페이지의 검색 메타데이터나 검색엔진 발견 경로가
# 함께 달라진다. 배포 후 sitemap 전체를 알리는 편이 일부 _posts 만 알리는 것보다
# 정확하다. _layouts 는 파일 추가/삭제까지 잡기 위해 prefix 로 관리한다.
GLOBAL_SEO_FILES = frozenset({
    "_config.yml",
    "_includes/head.html",
    "_plugins/posts-lastmod-hook.rb",
    "sitemap.xml",
    "robots.txt",
    "assets/robots.txt",
    "llms.txt",
    "llms-full.txt",
    "feed.xml",
    "assets/feed.xml",
    "rss.xml",
})
GLOBAL_SEO_PREFIXES = ("_layouts/",)

# 네이버와 Bing 각각의 수집 서버. 같은 프로토콜이라 본문(payload)은 동일하다.
ENDPOINTS = {
    "naver": "https://searchadvisor.naver.com/indexnow",
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


def _all_diff(base):
    """삭제를 포함해 사이트 전체의 변경 경로를 반환한다."""
    return subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD", "--"],
        cwd=ROOT, capture_output=True, text=True, timeout=30, check=True,
    ).stdout


def changed_files(base):
    """base 이후 변경된 모든 경로. 전역 파일 삭제도 SEO 변경으로 감지한다."""
    for candidate in (base, "HEAD~1"):
        if not candidate:
            continue
        try:
            out = _all_diff(candidate)
        except (subprocess.SubprocessError, OSError) as exc:
            print(f"::warning::git diff {candidate} 실패 -> {exc}")
            continue
        return [line for line in out.splitlines() if line]
    return []


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


def is_global_seo_file(path):
    """한 번의 변경이 여러 canonical 페이지에 영향을 주는 파일인지 판별한다."""
    normalized = path.replace("\\", "/").lstrip("./")
    return (
        normalized in GLOBAL_SEO_FILES
        or normalized.startswith(GLOBAL_SEO_PREFIXES)
    )


def has_global_seo_change(paths):
    return any(is_global_seo_file(path) for path in paths)


def post_url(path, base_url):
    basename = os.path.basename(path)[:-3]
    slug = slugify(re.sub(r"^\d{4}-\d{2}-\d{2}-", "", basename))
    return f"{base_url}/posts/{urllib.parse.quote(slug)}/"


def sanitize_urls(urls, host, limit=MAX_URLS):
    """IndexNow 제약에 맞는 같은 host 의 HTTPS URL 만 순서대로 남긴다."""
    accepted = []
    seen = set()
    rejected = 0
    overflow = 0

    for raw_url in urls:
        url = str(raw_url).strip()
        try:
            parsed = urllib.parse.urlsplit(url)
        except ValueError:
            rejected += 1
            continue

        if (
            not url
            or parsed.scheme.lower() != "https"
            or parsed.netloc.casefold() != host.casefold()
            or parsed.fragment
            or any(ord(char) < 32 for char in url)
        ):
            rejected += 1
            continue

        normalized = urllib.parse.urlunsplit(
            ("https", host, parsed.path or "/", parsed.query, "")
        )
        if normalized in seen:
            continue
        seen.add(normalized)

        if len(accepted) >= limit:
            overflow += 1
            continue
        accepted.append(normalized)

    if rejected:
        print(
            f"::warning::동일 host의 HTTPS canonical URL이 아닌 {rejected}건을 제외했습니다."
        )
    if overflow:
        print(
            f"::warning::IndexNow 요청 상한 {limit:,}건을 넘어선 "
            f"{overflow}건을 제외했습니다."
        )
    return accepted


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def fetch_deployed_sitemap(base_url):
    """배포된 URL sitemap 의 최상위 <url><loc> 값만 읽는다.

    다운로드 또는 XML 파싱에 실패하면 None 을 반환한다. 호출자는 이때 기존의
    변경 포스트 전용 흐름으로 물러나야 한다.
    """
    sitemap_url = f"{base_url}/sitemap.xml"
    request = urllib.request.Request(
        sitemap_url,
        method="GET",
        headers={
            "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.1",
            "User-Agent": "opsoai-indexnow/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            document = response.read(MAX_SITEMAP_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        print(f"::warning::배포 sitemap 다운로드 실패 -> {exc}")
        return None

    if len(document) > MAX_SITEMAP_BYTES:
        print(
            "::warning::배포 sitemap 이 안전한 읽기 한도 "
            f"{MAX_SITEMAP_BYTES:,}바이트를 넘었습니다."
        )
        return None

    try:
        root = ET.fromstring(document)
    except (ET.ParseError, LookupError, ValueError) as exc:
        print(f"::warning::배포 sitemap XML 파싱 실패 -> {exc}")
        return None

    if _local_name(root.tag) != "urlset":
        print(
            "::warning::배포 sitemap 루트가 <urlset>이 아니어서 "
            "canonical URL을 읽지 못했습니다."
        )
        return None

    urls = []
    for entry in root:
        if _local_name(entry.tag) != "url":
            continue
        for child in entry:
            if _local_name(child.tag) == "loc" and child.text:
                urls.append(child.text.strip())
                break

    if not urls:
        print("::warning::배포 sitemap 에 <url><loc> URL이 없습니다.")
        return None

    return urls


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
    parsed_base = urllib.parse.urlsplit(base_url)
    if parsed_base.scheme.lower() != "https" or not parsed_base.netloc:
        raise SystemExit("_config.yml 의 url 은 host 를 포함한 HTTPS URL 이어야 합니다.")
    host = parsed_base.netloc
    sitemap_mode = False

    if args:
        urls = sanitize_urls(args, host)
    else:
        base = os.environ.get("INDEXNOW_BASE", "").strip() or "HEAD~1"
        paths = changed_files(base)
        post_urls = [post_url(path, base_url) for path in changed_posts(base)]

        if has_global_seo_change(paths):
            changed = [path for path in paths if is_global_seo_file(path)]
            print(f"전역 SEO 변경 감지: {', '.join(changed)}")
            sitemap_urls = fetch_deployed_sitemap(base_url)
            urls = sanitize_urls(sitemap_urls or [], host)
            if urls:
                sitemap_mode = True
                print(f"배포 sitemap canonical URL {len(urls)}건을 사용합니다.")
            else:
                print(
                    "::warning::배포 sitemap 을 사용할 수 없어 "
                    "변경된 포스트 URL만 제출합니다."
                )
                urls = sanitize_urls(post_urls, host)
        else:
            urls = sanitize_urls(post_urls, host)

    if not urls:
        print("색인 요청할 URL이 없습니다.")
        return

    print(f"후보 {len(urls)}건")
    # sitemap 은 방금 끝난 배포 결과에서 읽었으므로 수천 건을 다시 HEAD 하지 않는다.
    # 명시 URL과 변경 포스트는 기존대로 실제 200 응답을 확인한 뒤 제출한다.
    live = urls if dry_run or sitemap_mode else [url for url in urls if is_live(url)]
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
