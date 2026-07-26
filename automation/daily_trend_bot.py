import os
import re
import json
import datetime
import html
import ipaddress
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import yaml
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
FALLBACK_THUMBNAIL = "/assets/img/logo.png"
NEWS_WINDOW_HOURS = max(24, min(168, int(os.environ.get("AI_NEWS_WINDOW_HOURS", "72"))))
MAX_NEWS_AGE_DAYS = max(2, min(14, int(os.environ.get("AI_NEWS_MAX_AGE_DAYS", "7"))))
HTTP_TIMEOUT = max(5, min(30, int(os.environ.get("AI_NEWS_HTTP_TIMEOUT", "12"))))
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
# Preview models first (best quality), then stable aliases as a safety net so the
# pipeline keeps working even after a preview model is retired.
FALLBACK_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-latest",
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
    return genai.Client(api_key=api_key)

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

def find_trending_topic(client):
    """
    Uses Gemini with Google Search to find consequential, newly published AI news.
    GitHub Trending and repository popularity are explicitly excluded as topic sources.
    """
    now = kst_now()
    history = recent_news_history()
    print(f"최근 {NEWS_WINDOW_HOURS}시간의 글로벌 AI 뉴스를 검색합니다...")
    prompt = f"""
You are the real-time news desk for a global AI publication.
The current time is {now.isoformat(timespec='minutes')}.
Use Google Search to find and rank 10-15 consequential AI stories that were
actually announced, released, published, filed, or reported in the last
{NEWS_WINDOW_HOURS} hours.

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
  older than {MAX_NEWS_AGE_DAYS} days.
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
                if not recent_publication(item.get("published_at"), now=now):
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
                    "source_urls": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": ["text", "source_urls"]
            }
        },
        "unknowns": {"type": "ARRAY", "items": {"type": "STRING"}}
    },
    "required": [
        "verified", "reason", "event_status", "published_at",
        "sources", "facts", "unknowns"
    ]
}


def verify_news_candidate(client, candidate):
    """Re-research the chosen story and build a source-locked fact pack."""
    now = kst_now()
    prompt = f"""
You are OPSOAI's independent AI-news fact checker.
The current time is {now.isoformat(timespec='minutes')}.
Use Google Search to independently verify this candidate:

{json.dumps(candidate, ensure_ascii=False)}

[RULES]
- verified=true only when the concrete event occurred and is no older than
  {MAX_NEWS_AGE_DAYS} days.
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
    if not raw.get("verified") or not recent_publication(raw.get("published_at"), now=now):
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
            or not recent_publication(published, now=now)
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
            facts.append({"text": text, "source_urls": list(dict.fromkeys(urls))})

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
    }

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


def _article_errors(post, evidence):
    content = post.get("content") or ""
    errors = []
    positions = [content.find(heading) for heading in NEWS_HEADINGS]
    if any(position < 0 for position in positions):
        errors.append("필수 뉴스 섹션 누락")
    elif positions != sorted(positions):
        errors.append("뉴스 섹션 순서 오류")
    if len(re.sub(r"\s+", "", content)) < 1800:
        errors.append("본문이 너무 짧음")
    allowed = {canonical_url(source["url"]) for source in evidence["sources"]}
    linked = {
        canonical_url(url)
        for url in re.findall(r"\]\((https?://[^)\s]+)", content)
    }
    unsupported = sorted(url for url in linked if url and url not in allowed)
    if unsupported:
        errors.append("검증 원문 밖 링크 포함: " + ", ".join(unsupported[:3]))
    if re.search(r"```(?:mermaid|chartjs)", content):
        errors.append("뉴스 글에 불필요한 생성형 도표 포함")
    return errors


def generate_blog_post(client, topic_data, evidence):
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
- description은 검색 결과용 70~160자, summary는 2~3문장이다.
- 본문은 H1 없이 2,800~4,500자 정도로 쓴다. 아래 H2 다섯 개만 정확히 이 순서로 쓴다.
  1. 무슨 일이 벌어진 걸까?
  2. 왜 지금 다들 이 이야기를 할까?
  3. 그래서 우리에게 뭐가 달라질까?
  4. 직접 써보거나 지켜볼 포인트
  5. 아직은 선을 그어야 할 부분
- 각 섹션 첫 문장은 그 질문에 바로 답해야 한다. 표는 비교가 정말 쉬워질 때 한 개만 허용한다.
- 이미지, Mermaid, Chart.js, 코드 블록은 넣지 않는다. 검증한 원문 이미지는 코드가 자동 배치한다.
- faq는 실제 검색 질문 3~4개와 각각 2~4문장의 직접 답변으로 만든다.
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
        return None
    try:
        post = json.loads(response_text)
    except (TypeError, ValueError) as exc:
        print(f"글 JSON 파싱 실패: {exc}")
        return None

    for key in ("title_korean", "title_english", "description", "summary"):
        post[key] = strip_emojis(str(post.get(key) or "")).strip()
    post["content"] = _normalize_news_markdown(post.get("content"))
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

    errors = _article_errors(post, evidence)
    if not all(post.get(key) for key in ("title_korean", "title_english", "description", "summary")):
        errors.append("제목 또는 메타 설명 누락")
    if not 60 <= len(post["description"]) <= 180:
        errors.append(f"메타 설명 길이 부적합: {len(post['description'])}자")
    if len(post["faq"]) < 3:
        errors.append("FAQ 3개 미만")
    if len(post["tags"]) < 5:
        errors.append("태그 5개 미만")
    if errors:
        print("글 출고 기준 미달: " + " / ".join(errors))
        return None
    return post

def _safe_slug(value):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(value or "")).strip("-").lower()
    return slug[:120] or f"ai-news-{kst_now():%H%M%S}"


def save_post(post_data, topic_data, evidence, *, now=None):
    """Save a news post using the existing blog layout and collected source visuals."""
    now = now or kst_now()
    filename = f"{now:%Y-%m-%d}-{_safe_slug(post_data.get('title_english'))}.md"
    filepath = os.path.realpath(os.path.join(POSTS_DIR, filename))
    if os.path.commonpath([os.path.realpath(POSTS_DIR), filepath]) != os.path.realpath(POSTS_DIR):
        raise RuntimeError("잘못된 게시물 경로")
    if os.path.exists(filepath):
        raise RuntimeError(f"같은 파일이 이미 존재합니다: {filename}")
    os.makedirs(POSTS_DIR, exist_ok=True)

    images = collect_source_images(evidence.get("sources") or [], limit=4)
    if images:
        print(f"원문 이미지 {len(images)}장을 수집했습니다.")
        hero_image = images[0]
        article_images = images[1:]
    else:
        print("사용 가능한 원문 이미지가 없어 기존 로고를 사용합니다.")
        hero_image = {
            "path": FALLBACK_THUMBNAIL,
            "alt": post_data["title_korean"],
            "credit": "OPSOAI",
        }
        article_images = []

    # Keep the prose clean: long publisher links become [1], [2] markers. Collected
    # source images are also placed in the body; when only one survives validation,
    # the hero is intentionally reused once so the article is not text-only.
    content = compact_source_citations(post_data["content"], evidence["sources"])
    content = insert_source_images(content, images)
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
        "title": post_data["title_korean"],
        "date": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "last_modified_at": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "categories": "Tech",
        "description": post_data["description"],
        "summary": post_data["summary"],
        "author": "AI Trend Bot",
        "article_type": "NewsArticle",
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
        "faq": faq,
        "sitemap": True,
    }
    if article_images:
        front_matter["article_images"] = article_images

    body = [content.rstrip(), "", "## 자주 묻는 질문", ""]
    for item in faq:
        body += [f"### {item['question']}", "", item["answer"], ""]
    body += ["## 직접 확인한 원문", "", source_list_html(evidence["sources"])]
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


def main():
    client = get_gemini_client()
    preflight_check(client)
    candidates = find_trending_topic(client)
    if not candidates:
        raise RuntimeError("발행 가능한 최신 AI 뉴스 후보를 찾지 못했습니다.")

    history = recent_news_history()
    for index, topic_data in enumerate(candidates, 1):
        print(f"\n후보 {index}/{len(candidates)} 재검증: {topic_data['headline']}")
        evidence = verify_news_candidate(client, topic_data)
        if not evidence:
            continue

        topic_data["published_at"] = evidence["published_at"]
        source_urls = [source["url"] for source in evidence["sources"]]
        if check_duplication(topic_data, history=history, source_urls=source_urls):
            print("  이미 다룬 사건이라 다음 후보로 넘어갑니다.")
            continue

        post_data = generate_blog_post(client, topic_data, evidence)
        if not post_data:
            print("  글 출고 기준을 통과하지 못해 다음 후보로 넘어갑니다.")
            continue

        save_post(post_data, topic_data, evidence)
        return

    raise RuntimeError("모든 후보가 중복 또는 팩트체크/품질 기준 미달입니다.")

if __name__ == "__main__":
    main()
