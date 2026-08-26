import os
import re
import json
import datetime
import html
import ipaddress
import math
import subprocess
import tempfile
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import yaml

from apply_tags import tags_for
from glossary import insert_box as insert_glossary_box
from make_thumbnail import generate_card
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

def fix_table_spacing(text):
    """kramdown (Jekyll) needs a blank line BEFORE and AFTER a markdown table.
    The model often glues a table directly under a bold header, so the whole block
    renders as a paragraph full of literal '|'. Insert the required blank lines at
    table boundaries (without touching the rows inside the table)."""
    is_row = lambda s: bool(re.match(r'^\s*\|.*\|', s))
    out = []
    for line in text.split("\n"):
        cur = is_row(line)
        prev = out[-1] if out else ""
        if cur and prev.strip() and not is_row(prev):          # entering table
            out.append("")
        elif not cur and line.strip() and out and is_row(out[-1]):  # leaving table
            out.append("")
        out.append(line)
    return "\n".join(out)


_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF\U0000FE0F\U0000200D]"
)


def strip_emojis(text):
    """Remove decorative emojis (title/headers/body). Rendered HTML collapses the
    leftover whitespace, so we only tidy heading markers for clean source."""
    if not text:
        return text
    text = _EMOJI.sub("", text)
    text = re.sub(r"(?m)^(#{1,6}) +", r"\1 ", text)   # tidy '### <emoji removed> Title'
    return text


def linkify_bare_urls(text):
    """Turn bare http(s) URLs into clickable [url](url) markdown — outside code fences
    and not already inside a markdown link/autolink/image/attribute."""
    parts = re.split(r"(```.*?```)", text, flags=re.S)   # keep fenced blocks intact
    url_re = re.compile(r'(?<![\(\[<"/=`])(https?://[^\s)\]<>"`]+)')
    for i in range(0, len(parts), 2):                    # even indices = non-code
        parts[i] = url_re.sub(lambda m: f"[{m.group(1)}]({m.group(1)})", parts[i])
    return "".join(parts)


def strip_fake_images(text):
    """Drop markdown images pointing at placeholder/invented hosts. The model used to
    insert ![...](https://via.placeholder.com/...) when it had no real image, which
    renders as an ugly gray box. Better to have no image than a fake one."""
    fake = re.compile(r'(?i)(via\.placeholder|placeholder\.com|dummyimage|example\.com|'
                      r'your[-_.]?image|image[-_.]?url|placehold\.co|fakeimg)')
    return "\n".join(l for l in text.split("\n")
                     if not (re.match(r'^\s*!\[', l) and fake.search(l)))


def _usable_image_url(url):
    """Verify that a collected source image is a public, non-trivial raster asset."""
    if not _public_https_url(url):
        return False
    low = str(url).lower()
    if any(token in low for token in (
        "favicon", "avatar", "logo.", "/logo/", "badge", "sprite", "tracking",
        "pixel", "spacer", "1x1",
    )):
        return False
    if re.search(r"\.(?:svg|ico)(?:$|\?)", low):
        return False
    try:
        response = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "image/avif,image/webp,image/png,image/jpeg,image/gif",
            },
            allow_redirects=True,
            stream=True,
        )
        content_type = response.headers.get("content-type", "").lower()
        content_length = response.headers.get("content-length")
        ok = (
            200 <= response.status_code < 400
            and content_type.startswith("image/")
            and "svg" not in content_type
            and (not content_length or int(content_length) >= 20_000)
        )
        response.close()
        return ok
    except (requests.RequestException, TypeError, ValueError):
        return False


def _article_image_candidates(source):
    """Collect declared share images and a few article-body images from one direct source."""
    source_url = canonical_url(source.get("url"))
    if direct_source_rejection_reason(source_url):
        return []
    try:
        response = requests.get(
            source_url,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            allow_redirects=True,
        )
        if response.status_code >= 400 or "html" not in response.headers.get("content-type", "").lower():
            return []
        soup = BeautifulSoup(response.text[:2_000_000], "html.parser")
    except requests.RequestException:
        return []

    candidates = []
    for selector, attr in (
        ('meta[property="og:image:secure_url"]', "content"),
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
        ('meta[name="twitter:image:src"]', "content"),
        ('link[rel="image_src"]', "href"),
    ):
        for node in soup.select(selector):
            value = node.get(attr)
            if value:
                candidates.append((urljoin(response.url, value), node.get("alt") or ""))

    for node in soup.select("article img, main img")[:8]:
        value = node.get("src") or node.get("data-src") or node.get("data-lazy-src")
        if value:
            candidates.append((urljoin(response.url, value), node.get("alt") or ""))

    output = []
    for url, alt in candidates:
        normalized = canonical_url(url)
        if not normalized or any(item["url"] == normalized for item in output):
            continue
        output.append({
            "url": normalized,
            "alt": strip_emojis(str(alt or "")).strip(),
        })
    return output


def collect_source_images(sources, limit=4):
    """Collect real images declared by verified source pages. No image generation."""
    images = []
    seen = set()
    ordered = sorted(
        sources or [],
        key=lambda source: 0 if source.get("tier") == "official" else 1,
    )
    for source in ordered:
        per_source = 0
        per_source_limit = 2 if source.get("tier") == "official" else 1
        for candidate in _article_image_candidates(source):
            if len(images) >= limit:
                return images
            image_url = candidate["url"]
            if image_url in seen or not _usable_image_url(image_url):
                continue
            seen.add(image_url)
            publisher = str(source.get("publisher") or source.get("name") or "원문 출처").strip()
            images.append({
                "path": image_url,
                "alt": candidate["alt"] or f"{publisher} 원문에 게시된 AI 뉴스 이미지",
                "caption": f"{publisher}가 원문과 함께 공개한 이미지입니다.",
                "credit": publisher,
                "source_url": canonical_url(source.get("url")),
            })
            per_source += 1
            if per_source >= per_source_limit:
                break
    return images


def _source_figure(image):
    source_url = html.escape(str(image.get("source_url") or ""), quote=True)
    credit = html.escape(str(image.get("credit") or "원문 출처"))
    caption = html.escape(str(image.get("caption") or "원문에 게시된 이미지입니다."))
    alt = html.escape(str(image.get("alt") or "AI 뉴스 원문 이미지"), quote=True)
    path = html.escape(str(image.get("path") or ""), quote=True)
    credit_html = (
        f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">출처: {credit}</a>'
        if source_url else f"출처: {credit}"
    )
    return (
        '<figure class="news-source-image">\n'
        f'  <img src="{path}" alt="{alt}" loading="lazy" decoding="async">\n'
        f"  <figcaption>{caption} {credit_html}</figcaption>\n"
        "</figure>"
    )


def insert_source_images(content, images):
    """Spread collected visuals through useful sections instead of making a gallery."""
    targets = (
        "## 왜 지금 다들 이 이야기를 할까?",
        "## 그래서 우리에게 뭐가 달라질까?",
        "## 직접 써보거나 지켜볼 포인트",
    )
    for target, image in zip(targets, images or []):
        content = content.replace(target, f"{_source_figure(image)}\n\n{target}", 1)
    return content


def compact_source_citations(content, sources):
    """Replace long inline publisher links with linked numeric source markers."""
    source_numbers = {
        canonical_url(source.get("url")): index
        for index, source in enumerate(sources or [], 1)
        if canonical_url(source.get("url"))
    }
    pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")

    def replace(match):
        number = source_numbers.get(canonical_url(match.group(2)))
        if not number:
            return match.group(0)
        label = html.escape(match.group(1).strip(), quote=True)
        return (
            f'<sup class="source-citation">'
            f'<a href="#source-{number}" aria-label="{label} 출처">[{number}]</a>'
            "</sup>"
        )

    return pattern.sub(replace, str(content or ""))


def source_list_html(sources):
    """Render the checked-source list with anchors targeted by numeric citations."""
    lines = ['<ol class="checked-source-list">']
    for index, source in enumerate(sources or [], 1):
        url = html.escape(str(source.get("url") or ""), quote=True)
        publisher = html.escape(str(source.get("publisher") or "원문"))
        title = html.escape(str(source.get("title") or "직접 원문"))
        published = html.escape(str(source.get("published_at") or ""))
        lines.append(
            f'  <li id="source-{index}"><a href="{url}" target="_blank" '
            f'rel="noopener noreferrer">{publisher} — {title}</a>'
            f"{f' ({published})' if published else ''}</li>"
        )
    lines.append("</ol>")
    return "\n".join(lines)


# Configuration
# Resolve relative to THIS file (not the caller's CWD) so it works whether run as
# `cd automation && python daily_trend_bot.py` (CI) or `python automation/daily_trend_bot.py`.
POSTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_posts")
MERMAID_VALIDATOR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "validate_mermaid.mjs",
)
FALLBACK_THUMBNAIL = "/assets/img/logo.png"
NEWS_WINDOW_HOURS = max(24, min(168, int(os.environ.get("AI_NEWS_WINDOW_HOURS", "72"))))
MAX_NEWS_AGE_DAYS = max(2, min(14, int(os.environ.get("AI_NEWS_MAX_AGE_DAYS", "7"))))
HTTP_TIMEOUT = max(5, min(30, int(os.environ.get("AI_NEWS_HTTP_TIMEOUT", "12"))))
GEMINI_HTTP_TIMEOUT_MS = max(
    60_000,
    min(600_000, int(os.environ.get("GEMINI_HTTP_TIMEOUT_MS", "180000"))),
)
USER_AGENT = "Mozilla/5.0 (compatible; OPSOAI-NewsBot/2.0; +https://www.opsoai.com/)"
TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "source",
    "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term",
}
SEARCH_HOSTS = {
    "google.com", "www.google.com", "news.google.com", "bing.com", "www.bing.com",
    "search.naver.com", "m.search.naver.com", "search.daum.net",
}
GENERIC_SOURCE_PATHS = {
    "", "/", "/blog", "/news", "/search", "/articles", "/resources",
    "/docs", "/documentation",
}
# Use one stable production model for discovery, fact-checking, writing, and preflight.
FALLBACK_MODELS = [
    "gemini-3.6-flash",
]


def kst_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))


def canonical_url(value):
    """Normalize a source URL while preserving meaningful query parameters."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return ""
        host = parsed.hostname.lower().rstrip(".")
        port = f":{parsed.port}" if parsed.port else ""
        query = urlencode([
            (key, val)
            for key, val in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in TRACKING_QUERY_KEYS
        ])
        path = re.sub(r"/+", "/", parsed.path or "/")
        if path != "/":
            path = path.rstrip("/")
        return urlunparse(("https", host + port, path, "", query, ""))
    except (TypeError, ValueError):
        return ""


def _public_https_url(value):
    """Reject private/literal network targets before model-supplied URLs are fetched."""
    normalized = canonical_url(value)
    if not normalized:
        return False
    parsed = urlparse(normalized)
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(host)
        if not address.is_global:
            return False
    except ValueError:
        pass
    return True


def direct_source_rejection_reason(value):
    """Only accept a specific article, announcement, paper, filing, or documentation page."""
    normalized = canonical_url(value)
    if not normalized or not _public_https_url(normalized):
        return "유효한 공개 HTTPS URL이 아님"
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if host in SEARCH_HOSTS:
        return "검색 결과 URL"
    path = (parsed.path or "/").lower().rstrip("/") or "/"
    if path in GENERIC_SOURCE_PATHS:
        return "홈페이지 또는 섹션 URL"
    if re.search(r"\.(?:png|jpe?g|gif|webp|svg|pdf|zip)(?:$|\?)", path):
        return "기사/발표 원문이 아닌 파일 URL"
    return None


def parse_iso_date(value):
    try:
        return datetime.date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def recent_publication(value, *, now=None, max_days=MAX_NEWS_AGE_DAYS):
    now = now or kst_now()
    published = parse_iso_date(value)
    if not published:
        return False
    age = (now.date() - published).days
    return -1 <= age <= max_days


def probe_source(url):
    """Best-effort HTTP verification without downloading a full article."""
    normalized = canonical_url(url)
    if direct_source_rejection_reason(normalized):
        return {"url": normalized, "status": None, "reachable": False}
    try:
        response = requests.get(
            normalized,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            },
            allow_redirects=True,
            stream=True,
        )
        status = int(response.status_code)
        final_url = canonical_url(response.url)
        content_type = response.headers.get("content-type", "").lower()
        response.close()
        return {
            "url": final_url if not direct_source_rejection_reason(final_url) else normalized,
            "status": status,
            "reachable": 200 <= status < 400 and (
                not content_type or "html" in content_type or "xml" in content_type
            ),
        }
    except requests.RequestException:
        return {"url": normalized, "status": None, "reachable": False}

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=GEMINI_HTTP_TIMEOUT_MS),
    )

def get_thinking_config(thinking_level="HIGH"):
    """
    Helper to create ThinkingConfig with fallback for compatibility.
    Some environments might have different validation/version for google-genai.
    """
    try:
        if thinking_level == "HIGH":
            # Try to use the enum if possible, or string
            return types.ThinkingConfig(thinking_level="HIGH")
        return types.ThinkingConfig(thinking_level=thinking_level)
    except Exception as e:
        print(f"Warning: ThinkingConfig validation failed ({e}). Fallback to include_thoughts=True.")
        # Fallback for older versions or validation issues
        return types.ThinkingConfig(include_thoughts=True)

def generate_content_with_fallback(client, contents, response_schema=None, tools=None, thinking_level=None):
    """
    Unified helper to generate content with fallback logic and optional thinking.
    """
    for model_id in FALLBACK_MODELS:
        try:
            print(f"Attempting with {model_id}...")
            
            # Prepare config
            gen_config = {
                "response_mime_type": "application/json" if response_schema else "text/plain",
            }
            if response_schema:
                gen_config["response_schema"] = response_schema
            if tools:
                gen_config["tools"] = tools
            if thinking_level:
                gen_config["thinking_config"] = get_thinking_config(thinking_level)

            response = client.models.generate_content(
                model=model_id, 
                contents=contents,
                config=types.GenerateContentConfig(**gen_config)
            )
            
            if response.text:
                return response.text
        except Exception as e:
            if "503" in str(e) or "overloaded" in str(e).lower():
                print(f"Model {model_id} overloaded (503). Trying fallback...")
                continue
            else:
                print(f"Error with {model_id}: {e}")
                continue
    return None

def find_trending_topic(
    client,
    *,
    window_hours=NEWS_WINDOW_HOURS,
    max_age_days=MAX_NEWS_AGE_DAYS,
):
    """
    Uses Gemini with Google Search to find consequential, newly published AI news.
    GitHub Trending and repository popularity are explicitly excluded as topic sources.
    """
    now = kst_now()
    history = recent_news_history()
    print(f"최근 {window_hours}시간의 글로벌 AI 뉴스를 검색합니다...")
    prompt = f"""
You are the real-time news desk for a global AI publication.
The current time is {now.isoformat(timespec='minutes')}.
Use Google Search to find and rank 10-15 consequential AI stories that were
actually announced, released, published, filed, or reported in the last
{window_hours} hours.

[INCLUDE]
- New AI models, product releases, material feature updates, important research,
  regulation/policy, security incidents, pricing/availability changes, or major
  business decisions with concrete impact.
- Stories useful to developers, founders, operators, creators, companies, or
  everyday AI users globally.
- Prefer an official announcement, official documentation, paper, filing, or
  incident notice as the primary source. Trusted original reporting is acceptable
  when no official source exists.

[EXCLUDE]
- GitHub Trending rankings, star counts, or a repository profile without a broader
  news event.
- Rumors, forecasts, recycled explainers, vague opinion pieces, and announcements
  older than {max_age_days} days.
- Search result URLs, homepages, category pages, or URLs with no printed date.
- Marketing partnerships that do not materially change a product or decision.

[OUTPUT RULES]
- Rank candidates by freshness, direct-source strength, practical impact, novelty,
  and broad interest. Famous company names alone are not a reason to rank high.
- source_url must be one specific HTTPS article/announcement page that directly
  supports the event.
- published_at must be the date printed by that source in YYYY-MM-DD. Never assume
  today's date.
- source_tier is official or trusted.
- event_status is announced, released, available, research, policy, or incident.
- Write headline, summary, why_it_matters, and search_query in English.
- trend_score is an integer from 0 to 100.

[RECENTLY PUBLISHED BY OPSOAI — do not repeat the same event]
{json.dumps(history[:50], ensure_ascii=False)}
"""
    
    response_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "topic_name": {"type": "STRING"},
                "headline": {"type": "STRING"},
                "summary": {"type": "STRING"},
                "why_it_matters": {"type": "STRING"},
                "event_status": {"type": "STRING"},
                "published_at": {"type": "STRING"},
                "source_name": {"type": "STRING"},
                "source_url": {"type": "STRING"},
                "source_tier": {"type": "STRING"},
                "entities": {"type": "ARRAY", "items": {"type": "STRING"}},
                "search_query": {"type": "STRING"},
                "trend_score": {"type": "NUMBER"}
            },
            "required": [
                "topic_name", "headline", "summary", "why_it_matters",
                "event_status", "published_at", "source_name", "source_url",
                "source_tier", "entities", "search_query", "trend_score"
            ]
        }
    }
    
    tools = [types.Tool(google_search=types.GoogleSearch())]
    
    # Retrieval task: No thinking config to avoid hangs/latency
    response_text = generate_content_with_fallback(
        client, 
        prompt, 
        response_schema=response_schema, 
        tools=tools, 
        thinking_level=None 
    )
    
    if response_text:
        try:
            data = json.loads(response_text)
            cleaned = []
            seen_urls = set()
            for item in data:
                source_url = canonical_url(item.get("source_url"))
                tier = str(item.get("source_tier") or "").strip().lower()
                if direct_source_rejection_reason(source_url):
                    continue
                if tier not in {"official", "trusted"}:
                    continue
                if not recent_publication(
                    item.get("published_at"),
                    now=now,
                    max_days=max_age_days,
                ):
                    continue
                if source_url in seen_urls:
                    continue
                item["source_url"] = source_url
                item["source_tier"] = tier
                item["entities"] = list(dict.fromkeys(
                    str(value).strip()
                    for value in (item.get("entities") or [])
                    if str(value).strip()
                ))[:10]
                item["trend_score"] = max(0, min(100, int(item.get("trend_score") or 0)))
                if not item.get("topic_name") or not item.get("headline"):
                    continue
                if check_duplication(item, history=history):
                    print(f"  중복 후보 제외: {item['headline']}")
                    continue
                seen_urls.add(source_url)
                cleaned.append(item)
            cleaned.sort(key=lambda item: item["trend_score"], reverse=True)
            print(f"검증 가능한 최신 후보 {len(cleaned)}건을 찾았습니다.")
            for item in cleaned:
                print(f"- [{item['trend_score']:02d}] {item['headline']} ({item['source_name']})")
            return cleaned
        except Exception as e:
            print(f"Error parsing trend data: {e}")
    return []

def _front_matter(filepath):
    try:
        with open(filepath, encoding="utf-8") as handle:
            raw = handle.read(120_000)
        if not raw.startswith("---"):
            return {}
        return yaml.safe_load(raw.split("---", 2)[1]) or {}
    except (OSError, ValueError, TypeError, yaml.YAMLError):
        return {}


def recent_news_history(days=45):
    """Read only news metadata; legacy GitHub-project posts do not block new stories."""
    history = []
    cutoff = kst_now().date() - datetime.timedelta(days=days)
    if not os.path.isdir(POSTS_DIR):
        return history
    for filename in sorted(os.listdir(POSTS_DIR), reverse=True):
        if not filename.endswith(".md"):
            continue
        match = re.match(r"(\d{4}-\d{2}-\d{2})-", filename)
        if match and parse_iso_date(match.group(1)) and parse_iso_date(match.group(1)) < cutoff:
            continue
        data = _front_matter(os.path.join(POSTS_DIR, filename))
        primary = canonical_url(data.get("news_source_url"))
        citations = data.get("source_citations") or []
        urls = [primary] if primary else []
        urls += [
            canonical_url(item.get("url"))
            for item in citations
            if isinstance(item, dict) and item.get("url")
        ]
        if not urls and not data.get("news_headline"):
            continue
        history.append({
            "title": str(data.get("title") or ""),
            "headline": str(data.get("news_headline") or ""),
            "publishedAt": str(data.get("news_published_at") or ""),
            "sourceUrls": list(dict.fromkeys(url for url in urls if url)),
            "entities": list(data.get("entities") or []),
        })
    return history[:100]


def daily_post_exists(*, now=None):
    """Return True once the daily news automation has produced a KST-dated post."""
    now = now or kst_now()
    prefix = f"{now:%Y-%m-%d}-"
    if not os.path.isdir(POSTS_DIR):
        return False
    for filename in os.listdir(POSTS_DIR):
        if not filename.startswith(prefix) or not filename.endswith(".md"):
            continue
        data = _front_matter(os.path.join(POSTS_DIR, filename))
        if data.get("automation") == "daily_ai_news" or data.get("news_headline"):
            return True
    return False


def _identity(value):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(value or "").casefold())


def check_duplication(candidate, *, history=None, source_urls=None):
    """Block the same event, without blocking future news about the same company."""
    history = history if history is not None else recent_news_history()
    urls = {
        canonical_url(url)
        for url in ([candidate.get("source_url")] + list(source_urls or []))
        if canonical_url(url)
    }
    headline = _identity(candidate.get("headline"))
    event_date = str(candidate.get("published_at") or "")[:10]
    entities = {_identity(value) for value in candidate.get("entities") or [] if _identity(value)}
    for item in history:
        if urls & set(item.get("sourceUrls") or []):
            return True
        old_headline = _identity(item.get("headline"))
        old_entities = {_identity(value) for value in item.get("entities") or [] if _identity(value)}
        same_date = event_date and event_date == str(item.get("publishedAt") or "")[:10]
        if (
            headline and old_headline
            and SequenceMatcher(None, headline, old_headline).ratio() >= 0.78
            and (same_date or bool(entities & old_entities))
        ):
            return True
    return False


EVIDENCE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "verified": {"type": "BOOLEAN"},
        "reason": {"type": "STRING"},
        "event_status": {"type": "STRING"},
        "published_at": {"type": "STRING"},
        "sources": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "url": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "publisher": {"type": "STRING"},
                    "published_at": {"type": "STRING"},
                    "tier": {"type": "STRING"}
                },
                "required": ["url", "title", "publisher", "published_at", "tier"]
            }
        },
        "facts": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    # 독자는 한국어로 읽는다. 영어 사실만 받으면 폴백 브리핑이
                    # 영어 목록 그대로 나가므로 번역을 같은 호출에서 함께 받는다.
                    "text_ko": {"type": "STRING"},
                    "source_urls": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": ["text", "text_ko", "source_urls"]
            }
        },
        "unknowns": {"type": "ARRAY", "items": {"type": "STRING"}},
        "unknowns_ko": {"type": "ARRAY", "items": {"type": "STRING"}},
        "headline_ko": {"type": "STRING"},
        # 글머리 다이어그램의 노드가 될 문구. 모델에게 맡기면 "사건 -> 영향 -> 한계"
        # 같은 빈 말이 나오므로, 검증된 사실에서 뽑은 구체적인 문구를 따로 받는다.
        "summary_flow": {"type": "ARRAY", "items": {"type": "STRING"}}
    },
    "required": [
        "verified", "reason", "event_status", "published_at",
        "sources", "facts", "unknowns", "unknowns_ko", "headline_ko",
        "summary_flow"
    ]
}


def verify_news_candidate(
    client,
    candidate,
    *,
    strict=True,
    max_age_days=MAX_NEWS_AGE_DAYS,
):
    """Re-research the chosen story and build a source-locked fact pack."""
    now = kst_now()
    prompt = f"""
You are OPSOAI's independent AI-news fact checker.
The current time is {now.isoformat(timespec='minutes')}.
Use Google Search to independently verify this candidate:

{json.dumps(candidate, ensure_ascii=False)}

[RULES]
- verified=true only when the concrete event occurred and is no older than
  {max_age_days} days.
- Include 2-5 direct sources. At least one must be an official announcement,
  documentation page, paper, filing, security notice, or regulator page.
- The other source should be independent trusted original reporting when available.
- Search result pages, homepages, category pages, image files, and social snippets
  are not sources.
- Use the publication date printed by each source in YYYY-MM-DD. Never infer today.
- Separate announced/planned from released/available. Preserve limited preview,
  region, price, benchmark, evaluation, and security-incident conditions.
- facts must contain 4-10 atomic, directly supported facts. Every fact lists the
  exact source URLs that support it.
- Put uncertain or conflicting claims in unknowns, never in facts.
- Return source tier as official or trusted. Write factual fields in English.

[KOREAN OUTPUT]
- The blog is written for Korean readers, so every fact also needs a Korean version.
- fact.text_ko is a natural Korean translation of fact.text. unknowns_ko translates
  unknowns in the same order. headline_ko is a Korean version of the candidate headline.
- Translate only. Never add a claim, number, or guess that is missing from the English text.
- Keep product, company, and model names in their original spelling. Keep numbers as printed.
- Write so that someone meeting the topic for the first time can follow it.
- Never use the middle dot character.

[SUMMARY FLOW]
- summary_flow is 4 to 6 short Korean noun phrases that map this story at a glance.
- Each phrase is at most 20 characters and must carry something specific to THIS story:
  a product name, a number, a date, a price, a company.
- Bad (banned, meaningless): 사건, 근거, 사용자 영향, 확인할 한계, 원문 확인, 도입 검토.
- Good: "8월 20일 OpenRouter 공개", "컨텍스트 100만 토큰", "프리뷰 기간 무료",
  "DeepSWE 80퍼센트", "개발사 미확인".
- Order them so the reader follows what happened, then what it offers, then what is
  still unknown. Use only facts and unknowns you just verified.
- Never use parentheses, brackets, colons, quotation marks, or the middle dot.
"""
    response_text = generate_content_with_fallback(
        client,
        prompt,
        response_schema=EVIDENCE_SCHEMA,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        thinking_level="HIGH",
    )
    if not response_text:
        return None
    try:
        raw = json.loads(response_text)
    except (TypeError, ValueError):
        return None
    if not raw.get("verified") or not recent_publication(
        raw.get("published_at"),
        now=now,
        max_days=max_age_days,
    ):
        print(f"  팩트체크 탈락: {raw.get('reason') or '최신 사건으로 검증되지 않음'}")
        return None

    sources = []
    source_map = {}
    for source in raw.get("sources") or []:
        url = canonical_url(source.get("url"))
        tier = str(source.get("tier") or "").strip().lower()
        published = str(source.get("published_at") or "")[:10]
        if (
            direct_source_rejection_reason(url)
            or tier not in {"official", "trusted"}
            or not recent_publication(published, now=now, max_days=max_age_days)
            or url in source_map
        ):
            continue
        probe = probe_source(url)
        normalized = {
            "url": probe["url"] or url,
            "title": str(source.get("title") or "").strip(),
            "publisher": str(source.get("publisher") or "").strip(),
            "published_at": published,
            "tier": tier,
            "reachable": bool(probe["reachable"]),
            "http_status": probe["status"],
        }
        source_map[url] = normalized
        source_map[normalized["url"]] = normalized
        sources.append(normalized)

    unique_sources = []
    seen = set()
    for source in sources:
        if source["url"] not in seen:
            seen.add(source["url"])
            unique_sources.append(source)
    sources = unique_sources
    allowed_urls = {source["url"] for source in sources}
    facts = []
    for fact in raw.get("facts") or []:
        urls = []
        for value in fact.get("source_urls") or []:
            normalized = canonical_url(value)
            mapped = source_map.get(normalized)
            final_url = mapped["url"] if mapped else normalized
            if final_url in allowed_urls:
                urls.append(final_url)
        text = str(fact.get("text") or "").strip()
        if text and urls:
            facts.append({
                "text": text,
                "text_ko": str(fact.get("text_ko") or "").strip(),
                "source_urls": list(dict.fromkeys(urls)),
            })

    errors = []
    if len(sources) < 2:
        errors.append("직접 원문 2개 미만")
    if not any(source["tier"] == "official" for source in sources):
        errors.append("공식 원문 없음")
    if not any(source["reachable"] for source in sources):
        errors.append("HTTP로 확인된 원문 없음")
    if len({urlparse(source["url"]).hostname for source in sources}) < 2:
        errors.append("독립된 두 출처가 아님")
    if len(facts) < 4:
        errors.append("직접 근거가 연결된 사실 4개 미만")
    if errors:
        print("  팩트체크 출고 기준 미달: " + " / ".join(errors))
        if strict or not sources or not facts:
            return None
    return {
        "verified": True,
        "reason": str(raw.get("reason") or "").strip(),
        "event_status": str(raw.get("event_status") or candidate.get("event_status") or "").strip(),
        "published_at": str(raw.get("published_at") or candidate.get("published_at"))[:10],
        "sources": sources,
        "facts": facts,
        "unknowns": [
            str(value).strip() for value in (raw.get("unknowns") or []) if str(value).strip()
        ],
        "unknowns_ko": [
            str(value).strip() for value in (raw.get("unknowns_ko") or []) if str(value).strip()
        ],
        "headline_ko": str(raw.get("headline_ko") or "").strip(),
        "summary_flow": [
            str(value).strip() for value in (raw.get("summary_flow") or []) if str(value).strip()
        ],
        "quality_warnings": errors,
    }


def candidate_fallback_evidence(candidate):
    """Build a last-resort fact pack from the discovery result and its direct URL."""
    url = canonical_url(candidate.get("source_url"))
    if direct_source_rejection_reason(url):
        return None
    published = str(candidate.get("published_at") or "")[:10]
    if not parse_iso_date(published):
        published = kst_now().date().isoformat()
    probe = probe_source(url)
    source_url = probe["url"] or url
    facts = []
    for value in (
        candidate.get("headline"),
        candidate.get("summary"),
        candidate.get("why_it_matters"),
    ):
        text = str(value or "").strip()
        if text and text not in {item["text"] for item in facts}:
            facts.append({"text": text, "source_urls": [source_url]})
    if not facts:
        return None
    tier = str(candidate.get("source_tier") or "trusted").strip().lower()
    if tier not in {"official", "trusted"}:
        tier = "trusted"
    return {
        "verified": False,
        "reason": "검색 단계의 직접 원문을 사용한 일일 발행 폴백",
        "event_status": str(candidate.get("event_status") or "reported").strip(),
        "published_at": published,
        "sources": [{
            "url": source_url,
            "title": str(candidate.get("headline") or candidate.get("topic_name") or "").strip(),
            "publisher": str(candidate.get("source_name") or "원문").strip(),
            "published_at": published,
            "tier": tier,
            "reachable": bool(probe["reachable"]),
            "http_status": probe["status"],
        }],
        "facts": facts,
        "unknowns": [
            "독립된 추가 원문과 세부 제공 조건은 발행 시점에 모두 확인되지 않았습니다."
        ],
        "quality_warnings": ["엄격한 재검증 대신 검색 단계의 직접 원문 1개를 사용함"],
    }

_HANGUL = re.compile(r"[가-힣]")


def _has_korean(value):
    return bool(_HANGUL.search(str(value or "")))


# 사실 문장에 흔한 일반 명사. 그림이 이 글의 것인지 가리는 데 도움이 안 된다.
_COMMON_WORDS = {
    "모델", "사용자", "개발자", "기능", "서비스", "발표", "공개", "제공", "지원",
    "이번", "현재", "가능", "확인", "경우", "내용", "관련", "때문", "위해", "통해",
    "그리고", "하지만", "있습니다", "합니다", "했습니다", "됩니다", "입니다",
}

_LABEL_BANNED = re.compile(r"[\[\](){}\"\'<>:;|`·]")
# 어떤 글에나 들어맞는 말은 그림에 넣을 값어치가 없다. 이 목록에 걸리면 버린다.
_EMPTY_LABELS = {
    "사건", "근거", "영향", "한계", "사용자 영향", "사용자와 개발자 영향",
    "확인할 한계", "도입 조건과 한계", "오늘의 ai 변화", "직접 원문 확인",
    "새 발표 확인", "도입 검토", "조건 확인", "기존 도구와 비교",
    "작은 작업에서 시험", "비용과 조건 재확인", "제한된 범위에서 적용",
    "추가 원문과 업데이트 대기", "요약", "결론",
}


def clean_flow_label(value, *, limit=22):
    """Mermaid 노드에 넣을 수 있게 다듬는다. 괄호와 콜론은 파서를 깨뜨린다."""
    label = _LABEL_BANNED.sub(" ", str(value or ""))
    label = re.sub(r"\s+", " ", label).strip(" -.,")
    if len(label) > limit:
        cut = label[:limit].rsplit(" ", 1)[0]
        label = cut if len(cut) >= limit // 2 else label[:limit]
    return label.strip()


def useful_flow_labels(evidence, *, limit=5):
    """검증 단계가 준 요약 문구 중 쓸 만한 것만 남긴다."""
    labels = []
    for value in evidence.get("summary_flow") or []:
        label = clean_flow_label(value)
        if not label or label.casefold() in _EMPTY_LABELS:
            continue
        if label in labels:
            continue
        labels.append(label)
    return labels[:limit]


def build_flow_diagram(evidence):
    """검증된 사실로 글머리 요약 흐름도를 만든다. 재료가 부족하면 그리지 않는다.

    빈 말로 채운 그림은 자리만 차지하고 독자에게 아무것도 주지 않는다.
    그럴 바에는 그림을 빼는 편이 낫다."""
    labels = useful_flow_labels(evidence)
    if len(labels) < 3:
        return ""
    lines = ["```mermaid", "flowchart TD"]
    names = [f"N{index}" for index in range(len(labels))]
    for name, label in zip(names, labels):
        lines.append(f'    {name}["{label}"]')
    for before, after in zip(names, names[1:]):
        lines.append(f"    {before} --> {after}")
    lines.append("```")
    return "\n".join(lines)


def diagram_is_empty_talk(code, evidence):
    """이 글에만 해당하는 말이 하나도 없는 그림인지 본다.

    글쓰기 프롬프트가 예시로 든 흐름을 모델이 그대로 노드 이름으로 베끼는 일이 잦다.
    숫자도 고유명사도 없는 그림은 어느 글에 붙여도 말이 되므로 이 글의 그림이 아니다."""
    text = str(code or "")
    if re.search(r"\d", text):
        return False

    # 이 사건에만 나오는 말이 하나라도 들어 있으면 이 글의 그림으로 본다.
    names = set()
    for source in evidence.get("sources") or []:
        names.add(str(source.get("publisher") or "").strip())
    for fact in evidence.get("facts") or []:
        names.update(re.findall(r"[A-Za-z][A-Za-z0-9.\-]{2,}", str(fact.get("text") or "")))
        names.update(
            word for word in re.findall(r"[가-힣]{2,}", str(fact.get("text_ko") or ""))
            if word not in _COMMON_WORDS
        )
    if any(name and name in text for name in names):
        return False

    # 구체적인 말이 없다고 바로 버리지는 않는다. 어느 글에나 붙는 상투적인 문구가
    # 실제로 들어 있을 때만 버린다. 애매하면 놔두는 편이 안전하다.
    flat = re.sub(r"\s+", " ", text).casefold()
    return any(empty in flat for empty in _EMPTY_LABELS)


def ensure_korean_evidence(client, evidence, *, headline=""):
    """사실과 한계 문장의 한국어본을 채운다.

    검증 단계는 원문과 글자 그대로 대조하려고 사실을 영어로 적는다. 수치 검증도 그
    영어 문장을 기준으로 돈다. 문제는 글쓰기가 실패해 폴백 브리핑으로 나갈 때인데,
    그때 영어 문장이 그대로 독자에게 노출됐다. 검증 호출이 한국어를 함께 돌려주므로
    보통은 할 일이 없고, 빠졌을 때만 한 번의 값싼 호출로 채운다."""
    facts = evidence.get("facts") or []
    unknowns = evidence.get("unknowns") or []
    unknowns_ko = list(evidence.get("unknowns_ko") or [])
    unknowns_ko += [""] * max(0, len(unknowns) - len(unknowns_ko))

    pending = []
    for index, fact in enumerate(facts):
        if not _has_korean(fact.get("text_ko")):
            pending.append(("fact", index, str(fact.get("text") or "").strip()))
    for index, value in enumerate(unknowns):
        if not _has_korean(unknowns_ko[index]):
            pending.append(("unknown", index, str(value).strip()))
    if headline and not _has_korean(evidence.get("headline_ko")):
        pending.append(("headline", 0, str(headline).strip()))
    pending = [item for item in pending if item[2]]
    # 요약 흐름도 재료도 같은 호출에서 함께 받는다. 폴백 브리핑은 이게 없으면
    # 그림 자리를 빈 말로 채우게 된다.
    need_flow = len(useful_flow_labels(evidence)) < 3
    if not pending and not need_flow:
        evidence["unknowns_ko"] = unknowns_ko
        return evidence

    numbered = "\n".join(f"{position}. {text}" for position, (_, _, text) in enumerate(pending))
    material = "\n".join(
        f"- {str(fact.get('text_ko') or fact.get('text') or '').strip()}"
        for fact in facts
    )
    flow_rule = ""
    if need_flow:
        flow_rule = """
[summary_flow]
이 사건을 한눈에 보여줄 4~6단계 요약 문구를 만들어라.
- 각 문구는 20자 이내의 한국어 명사구다.
- 제품명, 숫자, 날짜, 가격처럼 이 사건에만 해당하는 말을 반드시 담는다.
- 사건, 근거, 영향, 한계, 원문 확인, 도입 검토 같은 빈 말은 금지다.
  어느 글에 붙여도 말이 되는 문구는 쓰지 마라.
- 무슨 일이 있었는지, 무엇을 주는지, 아직 모르는 것이 무엇인지 순서로 늘어놓는다.
- 아래 사실에 없는 내용을 지어내지 마라.
- 괄호, 대괄호, 콜론, 따옴표, 가운뎃점을 쓰지 마라.

[사실]
""" + (material or "- 없음")
    prompt = f"""아래 문장을 한국어로 옮겨라.

[규칙]
- 원문에 없는 사실, 숫자, 추측을 절대 더하지 마라. 번역만 한다.
- 숫자는 원문 그대로 두고, 제품명과 회사명은 영문 표기를 유지한다.
- 처음 이 주제를 보는 사람도 이해할 수 있는 자연스러운 한국어로 쓴다.
- 가운뎃점 문자를 쓰지 마라.
- index 는 입력에 붙은 번호를 그대로 돌려준다.

{numbered or "- 번역할 문장 없음"}
{flow_rule}
"""
    schema = {
        "type": "OBJECT",
        "properties": {
            "translations": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "index": {"type": "NUMBER"},
                        "korean": {"type": "STRING"},
                    },
                    "required": ["index", "korean"],
                },
            },
            "summary_flow": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["translations", "summary_flow"],
    }
    response_text = generate_content_with_fallback(
        client, prompt, response_schema=schema, tools=None, thinking_level=None
    )
    translations = {}
    if response_text:
        try:
            payload = json.loads(response_text) or {}
            for item in payload.get("translations") or []:
                position = int(item.get("index"))
                korean = str(item.get("korean") or "").strip()
                if korean:
                    translations[position] = korean
            if need_flow and payload.get("summary_flow"):
                evidence["summary_flow"] = [
                    str(value).strip() for value in payload["summary_flow"] if str(value).strip()
                ]
        except (TypeError, ValueError, AttributeError) as exc:
            print(f"  번역 응답 파싱 실패: {exc}")
    if pending and not translations:
        # 번역이 실패해도 발행은 막지 않는다. 영어 문장이라도 원문 근거는 남는다.
        print("::warning:: 한국어 번역을 받지 못해 원문 문장을 그대로 싣습니다.")

    for position, (kind, index, _) in enumerate(pending):
        korean = translations.get(position)
        if not korean:
            continue
        if kind == "fact":
            facts[index]["text_ko"] = korean
        elif kind == "unknown":
            unknowns_ko[index] = korean
        else:
            evidence["headline_ko"] = korean

    evidence["unknowns_ko"] = unknowns_ko
    return evidence


NEWS_HEADINGS = (
    "## 무슨 일이 벌어진 걸까?",
    "## 왜 지금 다들 이 이야기를 할까?",
    "## 그래서 우리에게 뭐가 달라질까?",
    "## 직접 써보거나 지켜볼 포인트",
    "## 아직은 선을 그어야 할 부분",
)


def _load_news_prompt():
    config_path = os.path.join(os.path.dirname(__file__), "prompt_config.json")
    try:
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
        block = config.get("daily_ai_news_bot") or config.get("daily_trend_bot") or {}
        return str(block["system_prompt"])
    except (OSError, ValueError, TypeError, KeyError):
        return (
            "검증된 직접 원문만 바탕으로 최신 AI 뉴스를 쉽고 재미있게 설명하는 "
            "한국어 파워블로거다. 사실과 해석을 분리하고 과장하지 않는다."
        )


def _normalize_news_markdown(content):
    text = str(content or "").replace("\\n", "\n").strip()
    # Remove any model-invented image before heading normalization; consuming the
    # whitespace afterwards at a later stage can glue the first H2 to the intro.
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    for heading in NEWS_HEADINGS:
        text = re.sub(
            rf"\s*{re.escape(heading)}\s*",
            f"\n\n{heading}\n\n",
            text,
            count=1,
        )
    text = re.sub(r"(?m)^#(?!#)\s+.*(?:\n|$)", "", text)
    text = strip_fake_images(strip_emojis(text))
    text = linkify_bare_urls(text)
    return fix_table_spacing(re.sub(r"\n{3,}", "\n\n", text).strip())


def _fenced_blocks(content, language):
    """Return the bodies of fenced blocks for one exact language."""
    return re.findall(
        rf"```{re.escape(language)}[ \t]*\n(.*?)\n```",
        str(content or ""),
        flags=re.S | re.I,
    )


def _promote_first_mermaid(content):
    """Move the first Mermaid block to the very start as the article overview."""
    text = str(content or "").strip()
    match = re.search(
        r"```mermaid[ \t]*\r?\n.*?\r?\n```",
        text,
        flags=re.S | re.I,
    )
    if not match:
        return text
    overview = match.group(0).strip()
    remainder = (text[:match.start()] + text[match.end():]).strip()
    remainder = re.sub(r"\n{3,}", "\n\n", remainder)
    return f"{overview}\n\n{remainder}".strip()


def _validate_mermaid_codes(codes):
    """Parse Mermaid diagrams with the same JS package used by the automation."""
    diagrams = [str(code or "").strip() for code in codes]
    if not diagrams:
        return []
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            encoding="utf-8",
            delete=False,
        ) as handle:
            json.dump(diagrams, handle, ensure_ascii=False)
            temporary = handle.name
        result = subprocess.run(
            ["node", MERMAID_VALIDATOR, temporary],
            cwd=os.path.dirname(MERMAID_VALIDATOR),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "validator failed").strip()
            return [{"ok": False, "error": message[:300]} for _ in diagrams]
        parsed = json.loads(result.stdout)
        if not isinstance(parsed, list) or len(parsed) != len(diagrams):
            raise ValueError("unexpected Mermaid validator output")
        return [
            {
                "ok": bool(item.get("ok")),
                "error": str(item.get("error") or "")[:300],
            }
            for item in parsed
        ]
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return [{"ok": False, "error": str(exc)[:300]} for _ in diagrams]
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


_FACT_NUMBER = re.compile(
    r"(?<![A-Za-z0-9])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?![A-Za-z0-9])"
)


def _verified_numeric_values(evidence):
    """Extract raw numeric values from fact-checked statements, without deriving any."""
    values = set()
    for fact in evidence.get("facts") or []:
        for token in _FACT_NUMBER.findall(str(fact.get("text") or "")):
            try:
                value = float(token.replace(",", ""))
                if math.isfinite(value):
                    values.add(value)
            except ValueError:
                continue
    return values


def _validate_chartjs_code(code, evidence):
    """Accept only small, declarative Chart.js JSON grounded in verified facts."""
    try:
        if len(str(code or "")) > 20_000:
            return False, "Chart.js JSON이 너무 큼"
        config = json.loads(str(code or ""))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return False, f"Chart.js JSON 파싱 실패: {exc}"

    if not isinstance(config, dict):
        return False, "Chart.js 최상위 값은 객체여야 함"
    if config.get("type") not in {"bar", "line", "pie", "doughnut", "polarArea", "radar"}:
        return False, "허용되지 않은 Chart.js 유형"
    if any(key in str(code) for key in ('"__proto__"', '"prototype"', '"constructor"')):
        return False, "안전하지 않은 Chart.js 키"

    data = config.get("data")
    labels = data.get("labels") if isinstance(data, dict) else None
    datasets = data.get("datasets") if isinstance(data, dict) else None
    if (
        not isinstance(labels, list)
        or not 2 <= len(labels) <= 20
        or not all(isinstance(label, str) and 0 < len(label) <= 120 for label in labels)
    ):
        return False, "Chart.js labels는 2~20개의 짧은 문자열이어야 함"
    if not isinstance(datasets, list) or not 1 <= len(datasets) <= 4:
        return False, "Chart.js datasets는 1~4개여야 함"

    chart_values = []
    for dataset in datasets:
        values = dataset.get("data") if isinstance(dataset, dict) else None
        if not isinstance(dataset, dict) or not str(dataset.get("label") or "").strip():
            return False, "모든 Chart.js dataset에 label이 필요함"
        if not isinstance(values, list) or len(values) != len(labels):
            return False, "Chart.js data와 labels 길이가 다름"
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False, "Chart.js data에는 숫자만 허용"
            numeric = float(value)
            if not math.isfinite(numeric):
                return False, "Chart.js data에 유한하지 않은 숫자 포함"
            chart_values.append(numeric)

    if len(chart_values) < 2:
        return False, "비교할 Chart.js 수치가 부족함"
    verified = _verified_numeric_values(evidence)
    unsupported = sorted({
        value for value in chart_values
        if not any(math.isclose(value, allowed, rel_tol=1e-9, abs_tol=1e-9) for allowed in verified)
    })
    if unsupported:
        return False, "검증 facts에 없는 수치: " + ", ".join(
            f"{value:g}" for value in unsupported[:5]
        )
    options = config.get("options")
    plugins = options.get("plugins") if isinstance(options, dict) else None
    title = plugins.get("title") if isinstance(plugins, dict) else None
    if (
        not isinstance(title, dict)
        or title.get("display") is not True
        or not str(title.get("text") or "").strip()
    ):
        return False, "Chart.js에 표시할 제목이 없음"
    return True, ""


def _remove_fenced_block(content, language, code):
    pattern = re.compile(
        rf"```{re.escape(language)}[ \t]*\r?\n{re.escape(code)}\r?\n```",
        flags=re.I,
    )
    return pattern.sub("", content, count=1)


def _mermaid_grounding_error(code, evidence):
    """Block active directives and numbers that did not pass the fact-check step."""
    text = str(code or "")
    lowered = text.lower()
    if len(text) > 20_000:
        return "Mermaid 코드가 너무 큼"
    if any(token in lowered for token in ("click ", "javascript:", "<script", "<iframe", "%%{")):
        return "Mermaid 외부 동작 또는 설정 지시문 포함"

    verified = _verified_numeric_values(evidence)
    unsupported = []
    for token in _FACT_NUMBER.findall(text):
        value = float(token.replace(",", ""))
        if not any(math.isclose(value, allowed, rel_tol=1e-9, abs_tol=1e-9)
                   for allowed in verified):
            unsupported.append(value)
    if unsupported:
        return "검증 facts에 없는 Mermaid 수치: " + ", ".join(
            f"{value:g}" for value in sorted(set(unsupported))[:5]
        )
    return ""


def _sanitize_news_visuals(content, evidence):
    """Keep up to five safe Mermaid blocks and one evidence-backed chart."""
    text = str(content or "")
    mermaid_codes = _fenced_blocks(text, "mermaid")
    if not mermaid_codes:
        return text, ["검증 가능한 Mermaid 다이어그램 없음"]

    mermaid_results = _validate_mermaid_codes(mermaid_codes)
    kept_mermaid = 0
    for code, result in zip(mermaid_codes, mermaid_results):
        grounding_error = _mermaid_grounding_error(code, evidence)
        if result["ok"] and not grounding_error and kept_mermaid < 5:
            kept_mermaid += 1
            continue
        reason = grounding_error or result["error"] or "허용 개수 초과"
        text = _remove_fenced_block(text, "mermaid", code)
        print(f"  Mermaid 제외: {reason}")
    if kept_mermaid == 0:
        return text, ["문법과 근거 검증을 통과한 Mermaid 다이어그램 없음"]

    chart_codes = _fenced_blocks(text, "chartjs")
    kept_chart = 0
    for code in chart_codes:
        valid, error = _validate_chartjs_code(code, evidence)
        if valid and kept_chart < 1:
            kept_chart += 1
            continue
        # A chart is optional. Removing an ungrounded or extra chart preserves the
        # article while preventing plausible-looking invented numbers from shipping.
        text = _remove_fenced_block(text, "chartjs", code)
        print(f"  Chart.js 제외: {error or '허용 개수 초과'}")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return _promote_first_mermaid(text), []


def _article_errors(post, evidence):
    content = post.get("content") or ""
    errors = []
    positions = [content.find(heading) for heading in NEWS_HEADINGS]
    if any(position < 0 for position in positions):
        errors.append("필수 뉴스 섹션 누락")
    elif positions != sorted(positions):
        errors.append("뉴스 섹션 순서 오류")
    if _visible_prose_length(content) < 3500:
        errors.append("실제 설명 본문이 너무 짧음")
    if not content.lstrip().lower().startswith("```mermaid"):
        errors.append("글 첫 부분에 전체 흐름 Mermaid가 없음")
    allowed = {canonical_url(source["url"]) for source in evidence["sources"]}
    linked = {
        canonical_url(url)
        for url in re.findall(r"\]\((https?://[^)\s]+)", content)
    }
    unsupported = sorted(url for url in linked if url and url not in allowed)
    if unsupported:
        errors.append("검증 원문 밖 링크 포함: " + ", ".join(unsupported[:3]))
    if len(_fenced_blocks(content, "mermaid")) not in {3, 4, 5}:
        errors.append("Mermaid 다이어그램은 3~5개 필요")
    if len(_fenced_blocks(content, "chartjs")) > 1:
        errors.append("Chart.js 차트 1개 초과")
    other_fences = [
        language.lower()
        for language in re.findall(r"```([A-Za-z0-9_-]+)", content)
        if language.lower() not in {"mermaid", "chartjs"}
    ]
    if other_fences:
        errors.append("허용되지 않은 코드 블록: " + ", ".join(sorted(set(other_fences))))

    content_without_fences = re.sub(r"```.*?```|~~~.*?~~~", " ", content, flags=re.S)
    headings = re.findall(r"(?m)^(#{1,6})\s+(.+?)\s*$", content_without_fences)
    if any(level == "#" for level, _ in headings):
        errors.append("본문에 H1 제목이 포함됨")
    h2_text = [heading for level, heading in headings if level == "##"]
    required_h2 = [heading.removeprefix("## ") for heading in NEWS_HEADINGS]
    if any(heading not in h2_text for heading in required_h2):
        errors.append("필수 뉴스 H2 소제목이 실제 제목으로 존재하지 않음")
    previous_level = 1
    for level, heading in headings:
        current_level = len(level)
        if current_level == 1:
            continue
        if previous_level == 1 and current_level != 2:
            errors.append(f"첫 본문 소제목이 H{current_level}: {heading}")
            break
        if current_level > previous_level + 1:
            errors.append(
                f"소제목 계층이 H{previous_level}에서 H{current_level}로 건너뜀: {heading}"
            )
            break
        previous_level = current_level

    first_heading = re.search(r"(?m)^#{1,6}\s+", content_without_fences)
    intro = content_without_fences[: first_heading.start()] if first_heading else content_without_fences
    if len(_visible_prose(intro)) < 60:
        errors.append("직접 답변 도입이 너무 짧음")
    return errors


_PROSE_FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
_PROSE_IMAGE = re.compile(r"!\[[^]\n]*\]\([^)\n]+\)")
_PROSE_LINK = re.compile(r"\[([^]\n]*)\]\([^)\n]+\)")
_PROSE_COMMENT = re.compile(r"<!--.*?-->", re.S)
# A comparison such as ``latency < 5 ms`` is prose, not an HTML tag.  Keep the
# matcher deliberately conservative and never let it consume another line.
_PROSE_HTML_TAG = re.compile(
    r"</?[A-Za-z][A-Za-z0-9:-]*(?:\s+[^>\n]*)?\s*/?>"
)


def _visible_prose(content):
    """Return reader-visible prose without diagrams, images, or Markdown syntax."""
    text = _PROSE_FENCE.sub(" ", str(content or ""))
    text = _PROSE_IMAGE.sub(" ", text)
    text = _PROSE_LINK.sub(lambda match: match.group(1) or " ", text)
    text = _PROSE_COMMENT.sub(" ", text)
    text = _PROSE_HTML_TAG.sub(" ", text)
    text = html.unescape(text)
    text = re.sub(r"(?m)^#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*(?:[-*+] |\d+[.)]\s+|>\s*)", "", text)
    text = re.sub(r"[`*_~|:-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _visible_prose_length(content):
    return len(re.sub(r"\s", "", _visible_prose(content)))


def _post_data_errors(post, evidence, *, visual_errors=()):
    """Apply the complete pre-save contract to a generated or relaxed news post."""
    if not isinstance(post, dict):
        return ["글 데이터가 객체가 아님"]

    errors = list(visual_errors)
    errors.extend(_article_errors(post, evidence))
    if not all(
        str(post.get(key) or "").strip()
        for key in ("title_korean", "title_english", "description", "summary")
    ):
        errors.append("제목 또는 메타 설명 누락")

    description = str(post.get("description") or "").strip()
    if not 80 <= len(description) <= 160:
        errors.append(f"메타 설명 길이 부적합: {len(description)}자")

    faq = post.get("faq") or []
    if not isinstance(faq, list) or not 3 <= len(faq) <= 5:
        errors.append("FAQ는 3~5개 필요")
    else:
        questions = set()
        for index, item in enumerate(faq, 1):
            if not isinstance(item, dict):
                errors.append(f"FAQ {index}가 객체가 아님")
                continue
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            if not question or not answer:
                errors.append(f"FAQ {index}의 질문 또는 답변이 비어 있음")
            if question in questions:
                errors.append(f"FAQ 질문 중복: {question}")
            questions.add(question)

    tags = post.get("tags") or []
    if not isinstance(tags, list) or len(tags) < 5:
        errors.append("태그 5개 미만")
    return list(dict.fromkeys(errors))


def _remove_unverified_links(content, evidence):
    """Keep only links that point to the selected direct sources."""
    allowed = {canonical_url(source["url"]) for source in evidence.get("sources") or []}

    def replace(match):
        label, url = match.group(1), match.group(2)
        return match.group(0) if canonical_url(url) in allowed else label

    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", replace, str(content or ""))


def _fallback_post_data(topic_data, evidence):
    """Create a small, source-linked post when every model-writing attempt fails."""
    topic = str(
        topic_data.get("topic_name")
        or (topic_data.get("entities") or ["AI"])[0]
        or "AI"
    ).strip()
    headline = str(topic_data.get("headline") or f"{topic} 최신 소식").strip()
    source = evidence["sources"][0]
    publisher = str(source.get("publisher") or "원문").strip()
    source_link = f"[{publisher}]({source['url']})"
    # 검증 단계의 사실은 영어다. 한국어본을 앞에 세우고 원문 문장은 뒤에 흐리게 남긴다.
    # 독자는 한국어로 읽고, 확인하고 싶은 사람은 인용된 원문 표현을 그대로 대조할 수 있다.
    def _bilingual(korean, english, suffix=""):
        korean = str(korean or "").strip()
        english = str(english or "").strip()
        primary = " ".join(part for part in (korean or english, suffix) if part)
        if korean and english and korean != english:
            return f'{primary}<br><span class="source-original">원문: {english}</span>'
        return primary

    fact_items = [
        # 출처 표시는 번역문 바로 뒤에 붙인다. 원문 문장 뒤로 밀리면 무엇의 근거인지 흐려진다.
        _bilingual(item.get("text_ko"), item.get("text"), source_link)
        for item in evidence.get("facts") or []
        if str(item.get("text_ko") or item.get("text") or "").strip()
    ]
    unknowns = [
        str(value).strip()
        for value in evidence.get("unknowns") or []
        if str(value).strip()
    ]
    unknowns_ko = list(evidence.get("unknowns_ko") or [])
    unknowns_ko += [""] * max(0, len(unknowns) - len(unknowns_ko))
    unknown_items = [
        _bilingual(unknowns_ko[index], value)
        for index, value in enumerate(unknowns)
    ]
    headline_ko = str(evidence.get("headline_ko") or "").strip()
    headline_display = headline_ko or headline
    headline_original = (
        f'<span class="source-original">원문 헤드라인: {headline}</span>\n\n'
        if headline_ko and headline and headline_ko != headline
        else ""
    )

    fact_text = "\n\n".join(
        f"- {item}" for item in fact_items[:5]
    ) or f"- {headline_display} 관련 직접 원문이 공개됐습니다. {source_link}"
    unknown_text = "\n\n".join(f"- {item}" for item in unknown_items[:4]) or (
        "- 가격, 지역별 제공 범위, 실제 도입 조건은 원문에서 다시 확인해야 합니다."
    )
    # 예전에는 여기에 "오늘의 AI 변화 -> 직접 원문 확인 -> 영향 -> 한계" 그림이 박혀
    # 있었다. 어느 글에 붙여도 말이 되는 그림은 읽는 사람에게 아무것도 주지 않는다.
    # 지금은 검증된 사실로 만든 요약 흐름만 넣고, 재료가 없으면 그림을 뺀다.
    flow_diagram = build_flow_diagram(evidence)
    lead_visual = f"{flow_diagram}\n\n" if flow_diagram else ""
    content = f"""{lead_visual}{topic} 관련 새 소식을 오늘 확인 가능한 직접 원문 범위에서 정리했습니다. 자동 검증 기준을 모두 충족하지 못한 날에도 발행을 건너뛰지 않기 위한 간결한 브리핑이며, 확인되지 않은 내용은 단정하지 않습니다. 원문이 영어인 문장은 한국어로 옮기고, 대조할 수 있도록 원문도 함께 남겼습니다.

{NEWS_HEADINGS[0]}

**한 줄 요약**: {headline_display}

{headline_original}발행일은 {evidence.get('published_at') or '원문 표기 기준'}이며, 아래 내용은 {source_link}에서 확인할 수 있는 범위만 담았습니다.

{fact_text}

{NEWS_HEADINGS[1]}

이 소식의 핵심은 새 기능이나 발표의 이름보다 실제 사용자와 개발자의 선택이 달라지는지에 있습니다. 지금 단계에서는 원문이 밝힌 내용과 아직 공개하지 않은 내용을 분리해서 보는 것이 안전합니다.

{NEWS_HEADINGS[2]}

도입을 검토한다면 현재 쓰는 도구와 바로 교체하기보다 작은 작업에서 먼저 비교해 보는 편이 좋습니다. 제공 지역, 요금, 데이터 처리 방식처럼 의사결정에 영향을 주는 조건은 실제 사용 전에 원문에서 다시 확인해야 합니다.

{NEWS_HEADINGS[3]}

첫째, 공식 제공 범위와 사용 조건을 확인합니다. 둘째, 기존 작업 흐름에서 시간을 줄여주는지 작은 예제로 비교합니다. 셋째, 발표 내용과 실제 일반 제공 상태가 같은지 구분합니다.

{NEWS_HEADINGS[4]}

{unknown_text}

추가 원문이 공개되거나 제공 조건이 바뀌면 판단도 달라질 수 있습니다. 따라서 이 글은 오늘 시점의 출발점으로 활용하고, 실제 도입 전에는 연결된 원문을 다시 확인하는 것이 좋습니다.
""".strip()
    description = (
        f"{topic} 관련 최신 AI 소식을 확인 가능한 직접 원문 범위에서 정리했습니다. "
        "발표 내용과 실제 영향, 도입 전에 다시 확인할 조건과 한계를 함께 살펴봅니다."
    )
    return {
        "title_korean": f"{topic} 업데이트, 오늘 확인할 핵심 포인트",
        "title_english": f"Daily AI Brief {topic} {evidence.get('published_at') or ''}",
        "description": description,
        "summary": (
            f"{headline} 소식을 직접 원문 범위에서 정리했습니다. "
            "확인된 내용과 아직 다시 확인해야 할 조건을 나눠 살펴봅니다."
        ),
        "content": _normalize_news_markdown(content),
        "tags": ["AI 뉴스", topic, "인공지능", "생성형 AI", "AI 트렌드"],
        "entities": list(dict.fromkeys(
            [topic]
            + [
                str(value).strip()
                for value in topic_data.get("entities") or []
                if str(value).strip()
            ]
        ))[:10],
        "faq": [
            {
                "question": f"{topic} 소식에서 오늘 확인된 내용은 무엇인가요?",
                "answer": (
                    f"{headline_display} 관련 내용이 직접 원문에서 확인됐습니다. "
                    "세부 조건은 글 하단 원문을 함께 확인하는 것이 안전합니다."
                ),
            },
            {
                "question": f"{topic}을 지금 바로 도입해도 되나요?",
                "answer": (
                    "작은 작업에서 먼저 비교한 뒤 결정하는 편이 좋습니다. "
                    "가격, 제공 지역, 데이터 처리 조건은 실제 도입 전에 다시 확인하세요."
                ),
            },
            {
                "question": "이 글에서 아직 확인되지 않은 부분은 무엇인가요?",
                # FAQ 는 프론트매터와 JSON-LD 로도 나가므로 HTML 없는 평문만 쓴다.
                "answer": next(
                    (text for text in (unknowns_ko + unknowns) if str(text).strip()),
                    None,
                ) or (
                    "세부 제공 조건과 실제 사용 환경의 차이는 추가 확인이 필요합니다."
                ),
            },
        ],
    }


def _relax_post_data(post, topic_data, evidence):
    """Repair a model draft enough to publish without introducing new claims."""
    fallback = _fallback_post_data(topic_data, evidence)
    if not isinstance(post, dict):
        return fallback
    for key in ("title_korean", "title_english", "description", "summary"):
        if not str(post.get(key) or "").strip():
            post[key] = fallback[key]
    content = _remove_unverified_links(post.get("content"), evidence)
    positions = [content.find(heading) for heading in NEWS_HEADINGS]
    if (
        any(position < 0 for position in positions)
        or positions != sorted(positions)
        or not content.lstrip().lower().startswith("```mermaid")
        or len(_fenced_blocks(content, "mermaid")) not in {3, 4, 5}
    ):
        content = fallback["content"]
    post["content"] = content
    post["tags"] = list(dict.fromkeys(
        list(post.get("tags") or []) + fallback["tags"]
    ))[:10]
    post["entities"] = list(dict.fromkeys(
        list(post.get("entities") or []) + fallback["entities"]
    ))[:12]
    faq = list(post.get("faq") or [])
    for item in fallback["faq"]:
        if len(faq) >= 3:
            break
        faq.append(item)
    post["faq"] = faq[:4]
    return post


def _validated_relaxed_post(post, topic_data, evidence):
    """Repair a draft, then run the same full contract again before returning it."""
    relaxed = _relax_post_data(post, topic_data, evidence)
    errors = _post_data_errors(relaxed, evidence)
    if errors:
        print("완화 글 재검증 실패: " + " / ".join(errors))
        return None
    return relaxed


def generate_blog_post(client, topic_data, evidence, *, strict=True):
    """Write one fact-locked Korean AI news feature in a lively blogger voice."""
    print(f"뉴스 글 작성: {topic_data['headline']}")
    prompt_text = f"""
{_load_news_prompt()}

[선정된 최신 AI 뉴스]
{json.dumps(topic_data, ensure_ascii=False)}

[재검증된 직접 원문과 사실 — 이것만 사실 근거로 사용]
{json.dumps(evidence, ensure_ascii=False)}

[출고 규칙]
- 모든 독자용 필드는 자연스러운 한국어로 쓴다. 회사명, 제품명, 모델명은
  원문 표기를 유지한다.
- facts에 있는 내용만 사실로 쓴다. unknowns는 모르는 사실 또는 한계로 명시한다.
- 수치, 가격, 날짜, 출시 범위, 프리뷰/지역/평가 조건을 절대 생략하거나 확대하지 않는다.
- 사실을 말한 문장 바로 옆에 [공식 발표 또는 매체명](검증된 URL)을 붙인다.
  저장 단계에서 짧은 숫자 각주로 자동 변환된다. evidence.sources에 없는 URL은
  절대 만들지 않는다.
- 첫 두 문장은 독자가 "그래서 내게 무슨 의미인데?"를 바로 알게 한다.
- 말투는 똑똑한 친구에게 설명하는 인기 파워블로거처럼 친근하고 리듬감 있게 쓴다.
  짧은 문장, 자연스러운 질문, 구체적인 예시를 섞되 억지 유행어나 호들갑은 금지한다.
- 보도자료를 번역한 듯한 문장, 교과서식 정의, 반복 요약, 의미 없는 전망,
  장황한 역사 설명은 넣지 않는다.
- 제목은 검색할 회사/제품명과 실제 변화를 앞쪽에 넣고, 사람이 누르고 싶을 만큼
  구체적으로 쓴다. 낚시성 표현, 이모지, 느낌표 도배는 금지한다.
- 제목은 핵심 검색어를 한 번만 자연스럽게 사용하고 같은 표현을 반복하지 않는다.
  description은 검색 결과만 읽어도 사건, 변화, 독자 영향을 이해할 수 있는 80~160자,
  summary는 독립적으로 인용해도 의미가 통하는 2~3문장이다.
- 본문은 H1 없이 4,200~6,000자의 실제 설명문으로 쓴다. Mermaid와 Chart.js 코드,
  표의 문법 문자는 이 분량에 포함하지 않는다. 아래 H2 다섯 개만 정확히 이 순서로 쓴다.
  1. 무슨 일이 벌어진 걸까?
  2. 왜 지금 다들 이 이야기를 할까?
  3. 그래서 우리에게 뭐가 달라질까?
  4. 직접 써보거나 지켜볼 포인트
  5. 아직은 선을 그어야 할 부분
- 각 섹션 첫 1~2문장은 검색과 답변 엔진이 그대로 인용해도 이해되도록 주어와 제품명을
  생략하지 않은 직접 답변으로 쓴다. 그 뒤에 이유와 예시를 붙인다.
- 회사, 제품, 모델의 정식 이름은 첫 등장에 명확히 쓰고, 동의어, 약칭, 핵심 검색어를
  억지로 반복하지 않는다. 표는 비교가 정말 쉬워질 때 한 개만 허용한다.
- 검증한 원문 이미지는 코드가 자동 배치하므로 Markdown 이미지는 만들지 않는다.
- content의 첫 요소는 반드시 전체 글을 한눈에 요약하는 Mermaid 다이어그램이어야 한다.
  도입 문단이나 설명 문장보다 먼저 ```mermaid 코드 블록을 배치한다.
  노드 이름에는 이 글에만 해당하는 말을 넣는다. 제품명, 숫자, 날짜, 가격, 회사 이름이다.
  나쁜 예(절대 금지): "오늘의 AI 변화" -> "직접 원문 확인" -> "사용자와 개발자 영향"
  -> "도입 조건과 한계". 어느 글에 붙여도 말이 되는 그림은 독자에게 아무것도 주지 않는다.
  좋은 예: "8월 20일 OpenRouter 공개" -> "컨텍스트 100만 토큰" -> "프리뷰 무료"
  -> "DeepSWE 80퍼센트" -> "개발사 미확인".
  노드는 4~7개로 하고, 각 노드는 20자 이내로 쓴다.
- Mermaid는 첫 전체 흐름도를 포함해 3~5개 넣는다. 최소한 ① 글 전체 요약,
  ② 사건 또는 제품 작동 흐름, ③ 독자의 도입 판단과 주의점 다이어그램을 각각 하나씩
  만든다. 셋 모두 노드 이름에 이 글의 구체적인 사실을 담는다. 일반론만 담긴 그림은
  넣지 말고, 그럴 바에는 그 그림을 빼라. flowchart, sequenceDiagram, timeline 등 내용에 맞는 형식을 섞고, 같은
  결론을 모양만 바꿔 반복하지 않는다. 노드와 라벨에도 facts와 unknowns에 있는
  내용만 쓰며 가짜 수치를 만들지 않는다.
- 비교 가능한 검증 수치가 2개 이상 있을 때만 Chart.js 차트를 최대 1개 넣는다.
  chartjs 코드 블록 안에는 주석 없는 순수 JSON만 쓰고 type, data.labels,
  data.datasets를 포함한다. 모든 dataset에는 label을 붙이고 options.plugins.title에는
  display: true와 명확한 text를 넣는다. data의 모든 숫자는 facts에 원문 그대로
  있어야 하며 계산값, 추정치, 임의 점수는 금지한다. 수치 비교가 부적절하면 차트는 생략한다.
- Mermaid와 Chart.js 외의 코드 블록은 넣지 않는다. 그림 앞뒤에는 독자가 무엇을
  봐야 하는지 한두 문장으로 설명하되, 똑같은 내용을 장황하게 반복하지 않는다.
- faq는 독자가 실제 검색창이나 AI 답변창에 물을 법한 서로 다른 질문 3~4개로 만든다.
  답변 첫 문장만 읽어도 결론이 나오게 하고, 뒤 문장에 조건, 가격, 제한을 덧붙인다.
- tags는 5~10개, entities는 원문 표기 3~10개다.
- title_english는 파일명에 쓸 간결한 영문 제목이며 사실을 과장하지 않는다.
"""
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "title_korean": {"type": "STRING"},
            "title_english": {"type": "STRING"},
            "description": {"type": "STRING"},
            "summary": {"type": "STRING"},
            "content": {"type": "STRING"},
            "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "entities": {"type": "ARRAY", "items": {"type": "STRING"}},
            "faq": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "question": {"type": "STRING"},
                        "answer": {"type": "STRING"},
                    },
                    "required": ["question", "answer"],
                },
            },
        },
        "required": [
            "title_korean", "title_english", "description", "summary",
            "content", "tags", "entities", "faq"
        ],
    }
    response_text = generate_content_with_fallback(
        client,
        prompt_text,
        response_schema=response_schema,
        tools=None,
        thinking_level="HIGH",
    )
    if not response_text:
        return None if strict else _validated_relaxed_post(None, topic_data, evidence)
    try:
        post = json.loads(response_text)
    except (TypeError, ValueError) as exc:
        print(f"글 JSON 파싱 실패: {exc}")
        return None if strict else _validated_relaxed_post(None, topic_data, evidence)
    if not isinstance(post, dict):
        return None if strict else _validated_relaxed_post(None, topic_data, evidence)

    for key in ("title_korean", "title_english", "description", "summary"):
        post[key] = strip_emojis(str(post.get(key) or "")).strip()
    post["content"] = _normalize_news_markdown(post.get("content"))
    post["content"], visual_errors = _sanitize_news_visuals(post["content"], evidence)
    post["tags"] = list(dict.fromkeys(
        strip_emojis(str(value)).strip()
        for value in (post.get("tags") or [])
        if strip_emojis(str(value)).strip()
    ))[:10]
    post["entities"] = list(dict.fromkeys(
        [
            strip_emojis(str(value)).strip()
            for value in (post.get("entities") or [])
            if strip_emojis(str(value)).strip()
        ]
        + [
            str(value).strip()
            for value in (topic_data.get("entities") or [])
            if str(value).strip()
        ]
    ))[:12]
    post["faq"] = [
        {
            "question": strip_emojis(str(item.get("question") or "")).strip(),
            "answer": strip_emojis(str(item.get("answer") or "")).strip(),
        }
        for item in (post.get("faq") or [])
        if item.get("question") and item.get("answer")
    ][:4]

    errors = _post_data_errors(post, evidence, visual_errors=visual_errors)
    if errors:
        print("글 출고 기준 미달: " + " / ".join(errors))
        if strict:
            return None
        return _validated_relaxed_post(post, topic_data, evidence)
    return post

def replace_empty_lead_diagram(content, evidence):
    """글머리 그림이 이 글과 무관한 빈 말이면 사실로 만든 그림으로 바꾼다.

    글쓰기 지시문이 예로 든 흐름을 모델이 노드 이름으로 그대로 베끼는 일이 잦다.
    바꿔 끼울 재료가 없으면 그냥 지운다. 빈 그림보다 없는 편이 낫다."""
    blocks = _fenced_blocks(content, "mermaid")
    if not blocks:
        return content
    first = blocks[0]
    if not diagram_is_empty_talk(first, evidence):
        return content
    replacement = build_flow_diagram(evidence)
    pattern = re.compile(r"```mermaid[ \t]*\n.*?\n```", re.S | re.I)
    if not pattern.search(content):
        return content
    if replacement:
        print("  글머리 다이어그램이 빈 말이라 사실 기반 요약으로 교체합니다.")
        return pattern.sub(lambda _: replacement, content, count=1)
    print("  글머리 다이어그램이 빈 말이고 대체할 재료가 없어 제거합니다.")
    return pattern.sub("", content, count=1).lstrip()


def _safe_slug(value):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "")).strip("-").lower()
    return slug[:120] or f"ai-news-{kst_now():%H%M%S}"


def save_post(post_data, topic_data, evidence, *, now=None):
    """Save a news post using the existing blog layout and collected source visuals."""
    validation_errors = _post_data_errors(post_data, evidence)
    if validation_errors:
        raise ValueError("저장 전 글 품질 검증 실패: " + " / ".join(validation_errors))

    now = now or kst_now()
    # 카드 이미지 파일명도 이 슬러그를 그대로 쓴다. 글 URL(/posts/<slug>/)과 맞춰 둔다.
    post_slug = _safe_slug(post_data.get("title_english"))
    filename = f"{now:%Y-%m-%d}-{post_slug}.md"
    filepath = os.path.realpath(os.path.join(POSTS_DIR, filename))
    if os.path.commonpath([os.path.realpath(POSTS_DIR), filepath]) != os.path.realpath(POSTS_DIR):
        raise RuntimeError("잘못된 게시물 경로")
    if os.path.exists(filepath):
        raise RuntimeError(f"같은 파일이 이미 존재합니다: {filename}")
    os.makedirs(POSTS_DIR, exist_ok=True)

    # Rewrites below are part of the publication contract, not cosmetic post-processing.
    # In particular, replacing an empty lead diagram can remove it when no grounded
    # summary is available.  Validate the transformed draft before image/card side
    # effects and once more after every final insertion so an invalid body is never saved.
    content = compact_source_citations(post_data["content"], evidence["sources"])
    content = replace_empty_lead_diagram(content, evidence)
    content = insert_glossary_box(content)
    transformed_post = dict(post_data)
    transformed_post["content"] = content
    transformed_errors = _post_data_errors(transformed_post, evidence)
    if transformed_errors:
        raise ValueError(
            "최종 변환 후 글 품질 검증 실패: " + " / ".join(transformed_errors)
        )

    images = collect_source_images(evidence.get("sources") or [], limit=4)
    if images:
        print(f"원문 이미지 {len(images)}장을 수집했습니다.")
        collected_hero = images[0]
        # Keep the source URL on the visible figure, but expose only valid
        # ImageObject fields in jekyll-seo-tag's NewsArticle JSON-LD.
        hero_image = {
            "path": collected_hero["path"],
            "alt": collected_hero["alt"],
            "caption": collected_hero["caption"],
            "creditText": collected_hero["credit"],
        }
        article_images = images[1:]
    else:
        # 로고로 대체하면 모든 글의 공유 썸네일이 똑같아진다. 제목과 태그를 얹은
        # 카드를 그 자리에서 만들어 글마다 다른 이미지가 나가게 한다.
        print("원문 이미지가 없어 제목 카드를 생성합니다.")
        card_tags = tags_for(post_data["title_korean"], content, "Tech")
        try:
            card_path = generate_card(
                slug=post_slug,
                title=post_data["title_korean"],
                category="Tech",
                tags=card_tags,
                date=now.strftime("%Y-%m-%d"),
            )
        except Exception as exc:  # 렌더 실패가 발행 자체를 막지는 않게 한다
            print(f"카드 생성 실패({exc}). 로고로 대체합니다.")
            card_path = FALLBACK_THUMBNAIL
        hero_image = {
            "path": card_path,
            "alt": post_data["title_korean"],
            "creditText": "OPSOAI",
        }
        article_images = []

    # Collected source images are placed in the body; when only one survives
    # validation, the hero is intentionally reused once so the article is not text-only.
    content = insert_source_images(content, images)
    transformed_post["content"] = content
    final_errors = _post_data_errors(transformed_post, evidence)
    if final_errors:
        raise ValueError(
            "최종 변환 후 글 품질 검증 실패: " + " / ".join(final_errors)
        )
    primary_source = next(
        (source for source in evidence["sources"] if source.get("tier") == "official"),
        evidence["sources"][0],
    )
    faq = [
        {
            "question": strip_emojis(str(item.get("question") or "")).strip(),
            "answer": strip_emojis(str(item.get("answer") or "")).strip(),
        }
        for item in post_data.get("faq") or []
        if item.get("question") and item.get("answer")
    ]
    front_matter = {
        "layout": "post",
        "automation": "daily_ai_news",
        "publication_mode": (
            "fallback" if evidence.get("quality_warnings") else "verified"
        ),
        "title": post_data["title_korean"],
        "date": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "last_modified_at": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "categories": "Tech",
        "description": post_data["description"],
        "summary": post_data["summary"],
        "article_type": "NewsArticle",
        "seo": {"type": "NewsArticle"},
        "image": hero_image,
        "news_headline": topic_data["headline"],
        "news_source_url": primary_source["url"],
        "news_published_at": evidence["published_at"],
        "source_citations": [
            {
                "name": source["publisher"],
                "url": source["url"],
                "published_at": source["published_at"],
            }
            for source in evidence["sources"]
        ],
        "entities": post_data["entities"],
        # 통제 어휘 기반 태그. Chirpy 관련글 추천이 태그 교집합으로 동작하므로
        # 기존 612편과 같은 어휘를 써야 새 글이 옛 글과 이어진다.
        "tags": tags_for(post_data["title_korean"], content, "Tech"),
        "faq": faq,
        "sitemap": True,
    }
    if _fenced_blocks(content, "mermaid"):
        front_matter["mermaid"] = True
    if _fenced_blocks(content, "chartjs"):
        front_matter["chart"] = True
    if article_images:
        front_matter["article_images"] = article_images

    body = [content.rstrip(), "", "## 자주 묻는 질문", ""]
    for item in faq:
        body += [f"### {item['question']}", "", item["answer"], ""]
    body += ["## 직접 확인한 원문", "", source_list_html(evidence["sources"])]
    if evidence.get("quality_warnings"):
        body += [
            "",
            "> 이 글은 하루 1건 발행 원칙에 따라 당일 확인 가능한 직접 원문 범위에서 "
            "작성했습니다. 독립 출처나 일부 세부 조건이 부족할 수 있으므로 실제 도입 "
            "전에는 연결된 원문을 다시 확인하세요.",
            "",
        ]
    else:
        body += [
            "",
            "> 이 글은 위 원문을 직접 확인해 작성했습니다. 가격, 기능 범위, 지역별 제공 "
            "여부는 게시 후 바뀔 수 있으니 실제 도입 전 공식 문서를 다시 확인하세요.",
            "",
        ]

    temporary = f"{filepath}.tmp"
    try:
        with open(temporary, "x", encoding="utf-8") as handle:
            handle.write("---\n")
            yaml.safe_dump(
                front_matter,
                handle,
                allow_unicode=True,
                sort_keys=False,
                width=1000,
            )
            handle.write("---\n\n")
            handle.write("\n".join(body))
        os.replace(temporary, filepath)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"게시물 저장 완료: {filepath}")
    print(f"직접 원문 {len(evidence['sources'])}개 / 검증 사실 {len(evidence['facts'])}개")
    if evidence.get("quality_warnings"):
        print("완화 발행: " + " / ".join(evidence["quality_warnings"]))
    return filepath

def preflight_check(client):
    """
    Fail LOUDLY (non-zero exit) if the API key is invalid/denied.
    Without this, a dead GEMINI_API_KEY makes news discovery return []
    and the run finishes green with no post — a silent outage that gives no
    red run and no alert email. This turns that into a visible failure.
    """
    try:
        client.models.generate_content(model=FALLBACK_MODELS[-1], contents="ping")
    except Exception as e:
        msg = str(e)
        if any(k in msg for k in ("API_KEY_INVALID", "API key not valid",
                                  "PERMISSION_DENIED", "UNAUTHENTICATED", "401", "403")):
            print(f"FATAL: GEMINI_API_KEY is invalid or unauthorized -> {e}")
            raise SystemExit(1)
        # Transient/other errors: don't block; the fallback loop will handle them.
        print(f"Preflight warning (non-fatal): {e}")


def _publish_from_candidates(client, candidates, history):
    """Try strict publishing first, then force one grounded fallback from the list."""
    fallback_options = []
    for index, topic_data in enumerate(candidates, 1):
        print(f"\n후보 {index}/{len(candidates)} 재검증: {topic_data['headline']}")
        evidence = verify_news_candidate(
            client,
            topic_data,
            strict=False,
            max_age_days=14,
        )
        if not evidence:
            evidence = candidate_fallback_evidence(topic_data)
        if not evidence:
            continue

        # 사실 문장은 영어로 검증된다. 독자에게 나가기 전에 한국어본을 확보한다.
        ensure_korean_evidence(client, evidence, headline=topic_data.get("headline"))

        topic_data["published_at"] = evidence["published_at"]
        source_urls = [source["url"] for source in evidence["sources"]]
        if check_duplication(topic_data, history=history, source_urls=source_urls):
            print("  이미 다룬 사건이라 다음 후보로 넘어갑니다.")
            continue

        if evidence.get("quality_warnings"):
            fallback_options.append((topic_data, evidence))
            continue

        post_data = generate_blog_post(client, topic_data, evidence)
        if post_data:
            return save_post(post_data, topic_data, evidence)
        print("  엄격한 글 출고 기준 미달, 완화 발행 후보로 보관합니다.")
        fallback_options.append((topic_data, evidence))

    for topic_data, evidence in fallback_options:
        print(f"\n일일 발행 폴백 적용: {topic_data['headline']}")
        post_data = generate_blog_post(
            client,
            topic_data,
            evidence,
            strict=False,
        )
        if post_data:
            return save_post(post_data, topic_data, evidence)
    return None


def main():
    force = os.environ.get("AI_NEWS_FORCE_PUBLISH", "").strip().lower() in {
        "1", "true", "yes"
    }
    if not force and daily_post_exists():
        print("오늘의 자동 뉴스 글이 이미 있어 추가 발행하지 않습니다.")
        return

    client = get_gemini_client()
    preflight_check(client)
    candidates = find_trending_topic(client)
    history = recent_news_history()
    published = _publish_from_candidates(client, candidates, history)
    if published:
        return

    print("기본 검색에서 발행하지 못해 최근 14일 범위로 후보를 넓힙니다.")
    broad_candidates = find_trending_topic(
        client,
        window_hours=336,
        max_age_days=14,
    )
    seen = {canonical_url(item.get("source_url")) for item in candidates}
    broad_candidates = [
        item for item in broad_candidates
        if canonical_url(item.get("source_url")) not in seen
    ]
    published = _publish_from_candidates(client, broad_candidates, history)
    if published:
        return

    raise RuntimeError("직접 원문이 있는 비중복 AI 뉴스 후보를 찾지 못했습니다.")

if __name__ == "__main__":
    main()
