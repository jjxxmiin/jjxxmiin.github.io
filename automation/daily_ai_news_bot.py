"""OPSOAI global AI trend news publishing automation.

하루 두 번 실행되는 각 회차에서 글 한 건을 만든다.

    news discovery -> editorial selection -> claim-ledger fact checking
    -> visual SEO/AEO/GEO article -> deterministic checks -> Jekyll post

The editor/researcher split, direct-source verification, publication-date checks,
deduplication, and high-risk claim controls are adapted from ``explainer_reel.py``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import ipaddress
import json
import os
import re
import socket
import subprocess
import tempfile
import textwrap
import unicodedata
from difflib import SequenceMatcher
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from zoneinfo import ZoneInfo

import requests
import yaml
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont


KST = ZoneInfo("Asia/Seoul")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.realpath(os.path.join(BASE_DIR, "..", "_posts"))
NEWS_IMAGES_DIR = os.path.realpath(os.path.join(BASE_DIR, "..", "assets", "img", "news"))
LOGO_PATH = os.path.realpath(os.path.join(BASE_DIR, "..", "assets", "img", "logo.png"))
PROMPT_CONFIG = os.path.join(BASE_DIR, "prompt_config.json")
MERMAID_VALIDATOR = os.path.join(BASE_DIR, "validate_mermaid.mjs")

DEFAULT_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-latest",
]
FALLBACK_MODELS = [
    model.strip()
    for model in os.environ.get("AI_NEWS_MODELS", ",".join(DEFAULT_MODELS)).split(",")
    if model.strip()
] or DEFAULT_MODELS
DISCOVERY_HOURS = max(24, min(168, int(os.environ.get("AI_NEWS_WINDOW_HOURS", "72"))))
MAX_SOURCE_AGE_DAYS = max(2, min(14, int(os.environ.get("AI_NEWS_MAX_SOURCE_AGE_DAYS", "7"))))
HTTP_TIMEOUT = max(5, min(30, int(os.environ.get("AI_NEWS_HTTP_TIMEOUT", "12"))))
USER_AGENT = "Mozilla/5.0 (compatible; OPSOAI-FactCheck/1.0; +https://www.opsoai.com/)"

SOURCE_TIERS = ("official", "trusted")
CLAIM_TYPES = ("fact", "number", "price", "availability", "interpretation")
TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "source",
}
SEARCH_HOSTS = {
    "google.com", "www.google.com", "news.google.com", "bing.com", "www.bing.com",
    "search.naver.com", "search.daum.net", "duckduckgo.com",
}
GENERIC_PATHS = {
    "", "/", "/blog", "/news", "/newsroom", "/press", "/products", "/updates",
    "/articles", "/resources", "/docs", "/documentation",
}
ASSET_SUFFIXES = (
    ".avif", ".gif", ".jpeg", ".jpg", ".mov", ".mp3", ".mp4", ".pdf",
    ".png", ".svg", ".webm", ".webp",
)


def kst_now() -> dt.datetime:
    return dt.datetime.now(KST)


def get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY가 없습니다")
    return genai.Client(api_key=api_key)


def _thinking_config(level: str = "HIGH"):
    try:
        return types.ThinkingConfig(thinking_level=level)
    except Exception:
        return types.ThinkingConfig(include_thoughts=True)


def generate_json(client, prompt, schema, *, search=False, thinking="HIGH"):
    tools = [types.Tool(google_search=types.GoogleSearch())] if search else None
    errors = []
    for model_id in FALLBACK_MODELS:
        try:
            print(f"  Gemini: {model_id}")
            config = {
                "response_mime_type": "application/json",
                "response_schema": schema,
            }
            if tools:
                config["tools"] = tools
            if thinking:
                config["thinking_config"] = _thinking_config(thinking)
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(**config),
            )
            if response.text:
                return json.loads(response.text)
        except Exception as exc:
            errors.append(f"{model_id}: {str(exc)[:180]}")
            print(f"    실패: {str(exc)[:180]}")
    raise RuntimeError("모든 Gemini 모델 호출 실패 / " + " / ".join(errors))


def preflight_check(client):
    try:
        client.models.generate_content(model=FALLBACK_MODELS[-1], contents="ping")
    except Exception as exc:
        message = str(exc)
        fatal = (
            "API_KEY_INVALID", "API key not valid", "PERMISSION_DENIED",
            "UNAUTHENTICATED", "401", "403",
        )
        if any(token in message for token in fatal):
            raise RuntimeError(f"GEMINI_API_KEY 인증 실패: {message}") from exc
        print(f"  사전 점검 경고(일시 오류로 간주): {message[:180]}")


def canonical_url(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    path = re.sub(r"/+", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        path,
        "",
        urlencode(query),
        "",
    ))


def direct_source_rejection_reason(value: str) -> str | None:
    url = canonical_url(value)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = (parsed.path or "/").lower().rstrip("/") or "/"
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return "HTTPS 직접 URL이 아님"
    if host in SEARCH_HOSTS or host.startswith("search."):
        return "검색 결과 URL"
    if path in GENERIC_PATHS or re.fullmatch(r"/[a-z]{2}(?:-[a-z]{2})?", path):
        return "홈페이지 또는 섹션 URL"
    if path.endswith(ASSET_SUFFIXES):
        return "기사/발표 원문이 아닌 파일 URL"
    return None


class SourceImageMetaParser(HTMLParser):
    """Extract share images explicitly declared by a source article."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}
        self.link_images = []

    def handle_starttag(self, tag, attrs):
        attributes = {
            str(key or "").lower(): str(value or "").strip()
            for key, value in attrs
        }
        if tag.lower() == "meta":
            key = (
                attributes.get("property")
                or attributes.get("name")
                or ""
            ).lower()
            content = attributes.get("content", "")
            if key and content and key not in self.values:
                self.values[key] = content
        elif tag.lower() == "link":
            rel = {
                value.lower()
                for value in attributes.get("rel", "").split()
            }
            href = attributes.get("href", "")
            if "image_src" in rel and href:
                self.link_images.append(href)

    def image_candidates(self):
        urls = []
        for key in (
            "og:image:secure_url",
            "og:image",
            "twitter:image",
            "twitter:image:src",
        ):
            value = self.values.get(key)
            if value and value not in urls:
                urls.append(value)
        for value in self.link_images:
            if value not in urls:
                urls.append(value)
        return urls

    @property
    def image_alt(self):
        return (
            self.values.get("og:image:alt")
            or self.values.get("twitter:image:alt")
            or ""
        ).strip()


def _safe_remote_url(value, *, resolve=False):
    """Reject local/private literal targets before any remote image request."""
    try:
        parsed = urlparse(str(value or "").strip())
    except ValueError:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username
        or parsed.password
        or host == "localhost"
        or host.endswith((".localhost", ".local", ".internal"))
    ):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not resolve:
            return True
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(
                    host, 443, type=socket.SOCK_STREAM
                )
            }
        except (OSError, ValueError):
            return False
        return bool(addresses) and all(address.is_global for address in addresses)
    return address.is_global


def _safe_streaming_get(url, *, headers, max_redirects=5):
    """Follow HTTPS redirects only after validating each destination."""
    current = url
    for _ in range(max_redirects + 1):
        if not _safe_remote_url(current, resolve=True):
            raise ValueError("remote URL did not resolve to a public HTTPS address")
        response = requests.get(
            current,
            timeout=HTTP_TIMEOUT,
            headers=headers,
            allow_redirects=False,
            stream=True,
        )
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response
        location = response.headers.get("location")
        response.close()
        if not location:
            raise ValueError("redirect response has no location")
        current = urljoin(current, location)
    raise ValueError("too many redirects")


def _bounded_response_bytes(response, *, limit):
    payload = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        payload.extend(chunk)
        if len(payload) > limit:
            raise ValueError(f"remote payload exceeds {limit} bytes")
    return bytes(payload)


def source_image_metadata(source):
    """Read image metadata from a verified article page, not image search."""
    source_url = canonical_url(source.get("url"))
    if not _safe_remote_url(source_url):
        return []
    response = _safe_streaming_get(
        source_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    )
    try:
        response.raise_for_status()
        final_url = canonical_url(response.url)
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            raise ValueError(f"source is not HTML: {content_type or 'unknown'}")
        payload = _bounded_response_bytes(response, limit=2 * 1024 * 1024)
    finally:
        response.close()
    parser = SourceImageMetaParser()
    parser.feed(payload.decode(response.encoding or "utf-8", errors="replace"))
    return [
        {
            "url": urljoin(final_url, candidate),
            "alt": parser.image_alt,
        }
        for candidate in parser.image_candidates()
    ]


def parse_iso_date(value) -> dt.date | None:
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        return None


def recent_publication(value, *, now=None, max_days=MAX_SOURCE_AGE_DAYS) -> bool:
    day = parse_iso_date(value)
    if not day:
        return False
    today = (now or kst_now()).astimezone(KST).date()
    age = (today - day).days
    return -1 <= age <= max_days


def _normalize_identity(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^0-9a-z가-힣]+", "", value)


def _front_matter(path):
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
        if not raw.startswith("---\n"):
            return {}
        payload = raw.split("---", 2)[1]
        return yaml.safe_load(payload) or {}
    except (OSError, ValueError, TypeError, yaml.YAMLError):
        return {}


def recent_post_history(limit=100):
    if not os.path.isdir(POSTS_DIR):
        return []
    rows = []
    for filename in sorted(os.listdir(POSTS_DIR), reverse=True):
        if not filename.endswith((".md", ".markdown")):
            continue
        data = _front_matter(os.path.join(POSTS_DIR, filename))
        rows.append({
            "title": str(data.get("title") or ""),
            "summary": str(data.get("summary") or data.get("description") or ""),
            "sourceUrl": canonical_url(data.get("news_source_url") or data.get("github_url") or ""),
            "entities": [str(item) for item in (data.get("entities") or [])],
            "date": str(data.get("date") or "")[:10],
        })
        if len(rows) >= limit:
            break
    return rows


def is_duplicate_story(candidate, history) -> bool:
    candidate_url = canonical_url(candidate.get("source_url"))
    identity = _normalize_identity(
        f"{candidate.get('headline', '')} {candidate.get('topic_name', '')}"
    )
    candidate_entities = {
        _normalize_identity(item)
        for item in candidate.get("entities") or []
        if _normalize_identity(item)
    }
    for item in history:
        if candidate_url and candidate_url == canonical_url(item.get("sourceUrl")):
            return True
        old_identity = _normalize_identity(f"{item.get('title', '')} {item.get('summary', '')}")
        if identity and old_identity and SequenceMatcher(None, identity, old_identity).ratio() >= 0.78:
            return True
        old_entities = {
            _normalize_identity(value)
            for value in item.get("entities") or []
            if _normalize_identity(value)
        }
        if len(candidate_entities) >= 2 and len(candidate_entities & old_entities) >= 2:
            return True
    return False


DISCOVERY_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "ref": {"type": "STRING"},
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
        },
        "required": [
            "ref", "topic_name", "headline", "summary", "why_it_matters",
            "event_status", "published_at", "source_name", "source_url",
            "source_tier", "entities", "search_query",
        ],
    },
}


def discover_news_candidates(client, *, now=None, history=None):
    now = now or kst_now()
    history = history or []
    history_payload = [
        {"title": row["title"], "sourceUrl": row["sourceUrl"], "entities": row["entities"]}
        for row in history[:50]
    ]
    prompt = f"""You are the real-time news desk for a global AI publication.
The current time is {now.isoformat(timespec='minutes')}. Use Google Search to find
8-12 consequential AI stories actually announced or reported within the last
{DISCOVERY_HOURS} hours.

[INCLUDE]
- New AI models, products, or features; important policy or regulation; confirmed
  business changes; research results; or pricing and availability changes.
- Stories with a concrete impact on developers, operators, founders, companies,
  creators, policymakers, or everyday AI users worldwide.
- An official announcement, documentation, filing, or paper first; reliable
  original reporting second.

[EXCLUDE]
- GitHub Trending rankings or a repository profile with no broader news event.
- Rumors, forecasts, negotiations, and plans framed as completed events.
- Sources with no verifiable publication date, search pages, homepages, or category pages.
- Promotional partnership releases without a material change, and recycled stories.

source_url must be a specific HTTPS page that directly supports the event.
published_at must be the date printed by that source in YYYY-MM-DD; never infer today's date.
event_status must be one of announced/released/available/research/policy/planned.
source_tier must be official or trusted.
Use unique refs n1,n2... and write headline, summary, and why_it_matters in English.

[RECENT PUBLISHING HISTORY — exclude the same event]
{json.dumps(history_payload, ensure_ascii=False)}
"""
    raw = generate_json(client, prompt, DISCOVERY_SCHEMA, search=True, thinking=None)
    cleaned = []
    seen_urls = set()
    for index, item in enumerate(raw if isinstance(raw, list) else [], 1):
        source_url = canonical_url(item.get("source_url"))
        published_at = str(item.get("published_at") or "")
        tier = str(item.get("source_tier") or "").lower()
        if direct_source_rejection_reason(source_url):
            continue
        if not recent_publication(published_at, now=now):
            continue
        if tier not in SOURCE_TIERS or source_url in seen_urls:
            continue
        candidate = {
            **item,
            "ref": f"n{index}",
            "source_url": source_url,
            "source_tier": tier,
            "entities": list(dict.fromkeys(
                str(value).strip() for value in (item.get("entities") or [])
                if str(value).strip()
            ))[:10],
        }
        if not candidate.get("headline") or not candidate.get("topic_name"):
            continue
        if is_duplicate_story(candidate, history):
            print(f"  중복 후보 제외: {candidate['headline']}")
            continue
        seen_urls.add(source_url)
        cleaned.append(candidate)
    for index, candidate in enumerate(cleaned, 1):
        candidate["ref"] = f"n{index}"
    return cleaned


EDITOR_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "selected_ref": {"type": "STRING"},
        "news_angle": {"type": "STRING"},
        "reader_question": {"type": "STRING"},
        "why_now": {"type": "STRING"},
        "practical_impact": {"type": "STRING"},
        "scores": {
            "type": "OBJECT",
            "properties": {
                "freshness": {"type": "NUMBER"},
                "utility": {"type": "NUMBER"},
                "evidence": {"type": "NUMBER"},
                "impact": {"type": "NUMBER"},
                "novelty": {"type": "NUMBER"},
            },
            "required": ["freshness", "utility", "evidence", "impact", "novelty"],
        },
        "risks": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": [
        "selected_ref", "news_angle", "reader_question", "why_now",
        "practical_impact", "scores", "risks",
    ],
}


def select_editorial_topic(client, candidates, history):
    if not candidates:
        raise RuntimeError("편집장이 고를 신선한 뉴스 후보가 없습니다")
    prompt = f"""You are the editor-in-chief of OPSOAI. Select exactly one story for
this publishing run and return only a ref present in candidates as selected_ref.

Rank by: 1) freshness, 2) strength of direct evidence, 3) practical global impact,
4) specificity of the event, and 5) novelty versus recent coverage. Do not select
a company merely because it is famous. Rank plans and negotiations below releases
unless the planning event itself materially changes decisions. Separate reported
facts from editorial interpretation and invent no numbers or performance claims.
Every score is from 0 to 5. Write all editorial fields in English.

[CANDIDATES]
{json.dumps(candidates, ensure_ascii=False)}

[RECENT PUBLISHING HISTORY]
{json.dumps(history[:30], ensure_ascii=False, default=str)}
"""
    editorial = generate_json(client, prompt, EDITOR_SCHEMA, search=False, thinking="HIGH")
    refs = {candidate["ref"] for candidate in candidates}
    if editorial.get("selected_ref") not in refs:
        raise RuntimeError("편집장 selected_ref가 후보 목록 밖입니다")
    if any(
        not isinstance(editorial.get("scores", {}).get(key), (int, float))
        or not 0 <= editorial["scores"][key] <= 5
        for key in ("freshness", "utility", "evidence", "impact", "novelty")
    ):
        raise RuntimeError("편집장 점수는 항목별 0~5여야 합니다")
    return editorial


EVIDENCE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "thesis": {"type": "STRING"},
        "sources": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "url": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "publisher": {"type": "STRING"},
                    "published_at": {"type": "STRING"},
                    "tier": {"type": "STRING"},
                    "reachable": {"type": "BOOLEAN"},
                },
                "required": [
                    "id", "url", "title", "publisher", "published_at", "tier", "reachable",
                ],
            },
        },
        "claims": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "text": {"type": "STRING"},
                    "type": {"type": "STRING"},
                    "evidence_ids": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "supported": {"type": "BOOLEAN"},
                    "confidence": {"type": "NUMBER"},
                },
                "required": [
                    "id", "text", "type", "evidence_ids", "supported", "confidence",
                ],
            },
        },
        "unknowns": {"type": "ARRAY", "items": {"type": "STRING"}},
        "forbidden_claims": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["thesis", "sources", "claims", "unknowns", "forbidden_claims"],
}


def probe_source(url):
    try:
        response = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            allow_redirects=True,
            stream=True,
        )
        status = int(response.status_code)
        final_url = canonical_url(response.url)
        response.close()
        return {
            "http_status": status,
            "http_verified": 200 <= status < 400,
            "final_url": final_url if not direct_source_rejection_reason(final_url) else canonical_url(url),
        }
    except requests.RequestException:
        return {"http_status": None, "http_verified": False, "final_url": canonical_url(url)}


def normalize_evidence(evidence, *, now=None):
    normalized_sources = []
    source_id_map = {}
    seen_urls = set()
    for source in evidence.get("sources") or []:
        url = canonical_url(source.get("url"))
        if direct_source_rejection_reason(url) or url in seen_urls:
            continue
        published = str(source.get("published_at") or "")
        if not recent_publication(published, now=now):
            continue
        tier = str(source.get("tier") or "").lower()
        if tier not in SOURCE_TIERS:
            continue
        probe = probe_source(url)
        new_id = f"s{len(normalized_sources) + 1}"
        source_id_map[str(source.get("id") or "")] = new_id
        normalized_sources.append({
            "id": new_id,
            "url": probe["final_url"] or url,
            "title": str(source.get("title") or "").strip(),
            "publisher": str(source.get("publisher") or "").strip(),
            "published_at": published,
            "tier": tier,
            # 모델의 reachable 판정과 실제 HTTP 판정을 모두 보존한다. 일부 언론의
            # 봇 차단(403)이 팩트 부재로 오판되지 않도록 HTTP 상태는 별도 기록한다.
            "reachable": bool(source.get("reachable")),
            "http_verified": probe["http_verified"],
            "http_status": probe["http_status"],
        })
        seen_urls.add(url)

    normalized_claims = []
    for claim in evidence.get("claims") or []:
        evidence_ids = [
            source_id_map[source_id]
            for source_id in (claim.get("evidence_ids") or [])
            if source_id in source_id_map
        ]
        supported = bool(claim.get("supported")) and bool(evidence_ids)
        normalized_claims.append({
            "id": f"c{len(normalized_claims) + 1}",
            "text": str(claim.get("text") or "").strip(),
            "type": str(claim.get("type") or "fact").lower(),
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
            "supported": supported,
            "confidence": max(0.0, min(1.0, float(claim.get("confidence") or 0))),
        })
    return {
        "thesis": str(evidence.get("thesis") or "").strip(),
        "sources": normalized_sources,
        "claims": normalized_claims,
        "unknowns": [str(value).strip() for value in evidence.get("unknowns") or [] if str(value).strip()],
        "forbidden_claims": [
            str(value).strip()
            for value in evidence.get("forbidden_claims") or []
            if str(value).strip()
        ],
    }


def evidence_errors(evidence):
    errors = []
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    claims = evidence.get("claims") if isinstance(evidence, dict) else None
    if not evidence.get("thesis"):
        errors.append("thesis 누락")
    if not isinstance(sources, list) or not sources:
        errors.append("직접 원문 없음")
        return errors
    if not any(source.get("tier") == "official" for source in sources):
        errors.append("당사자 공식 발표 또는 공식 문서 출처 없음")
    ids = {source.get("id") for source in sources}
    if not any(source.get("reachable") or source.get("http_verified") for source in sources):
        errors.append("도달 가능하다고 확인된 직접 원문 없음")
    if len({urlparse(source["url"]).hostname for source in sources}) < min(2, len(sources)):
        errors.append("모든 근거가 한 도메인에만 있음")
    supported_count = 0
    for claim in claims or []:
        if not claim.get("text") or claim.get("type") not in CLAIM_TYPES:
            errors.append(f"{claim.get('id', '?')} 주장 형식 오류")
            continue
        refs = claim.get("evidence_ids") or []
        if any(source_id not in ids for source_id in refs):
            errors.append(f"{claim.get('id', '?')} 미등록 출처 참조")
        if claim.get("supported"):
            supported_count += 1
            if claim.get("type") != "interpretation" and not refs:
                errors.append(f"{claim.get('id', '?')} 사실 주장에 직접 근거 없음")
    if supported_count < 3:
        errors.append("supported claim 3개 미만")
    return errors


def build_evidence_pack(client, candidate, editorial, *, now=None):
    now = now or kst_now()
    prompt = f"""You are OPSOAI's independent researcher and fact-checker. Use Google
Search to reinvestigate the selected story and build an English claim ledger.

[SELECTED STORY]
{json.dumps(candidate, ensure_ascii=False)}

[EDITORIAL ANGLE]
{json.dumps(editorial, ensure_ascii=False)}

[VERIFICATION RULES]
- Include at least one official announcement, security notice, documentation page,
  filing, or paper from a party to the event, plus reliable original reporting
  where available. Find at least two independent sources.
- Search results, image/CDN files, homepages, and section pages are not sources.
- Use only the publication date explicitly printed on a source, in YYYY-MM-DD.
- Link every factual, numeric, price, and availability claim to source ids that
  directly support it.
- Do not turn a goal, plan, negotiation, or forecast into a completed event.
- Mark unverified claims supported=false and put unsafe phrasing in forbidden_claims.
- Keep interpretation as type=interpretation and never present it as reported fact.
- For attacks and incidents, preserve whether events occurred in evaluation,
  research, controlled testing, or a production deployment.
- Detection, blocking, isolation, forensic analysis, and recovery are different.
  Do not change forensic analysis into "stopped the attack."
- Name a model and version only when a source in this search verifies it.
- source tier is official or trusted; claim type is one of {', '.join(CLAIM_TYPES)}.
- Use source ids s1..., claim ids c1..., and write every field in English.
- Never infer {now.date().isoformat()} as a source publication date.
"""
    raw = generate_json(client, prompt, EVIDENCE_SCHEMA, search=True, thinking="HIGH")
    evidence = normalize_evidence(raw, now=now)
    errors = evidence_errors(evidence)
    if errors:
        raise RuntimeError("claim ledger 검증 실패: " + " / ".join(errors))
    return evidence


BLOG_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "description": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "content": {"type": "STRING"},
        "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        "entities": {"type": "ARRAY", "items": {"type": "STRING"}},
        "key_takeaways": {"type": "ARRAY", "items": {"type": "STRING"}},
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
        "title", "description", "summary", "content", "tags", "entities",
        "key_takeaways", "faq",
    ],
}


def _load_system_prompt():
    try:
        with open(PROMPT_CONFIG, encoding="utf-8") as handle:
            config = json.load(handle)
        return str(config["daily_ai_news_bot"]["system_prompt"])
    except (OSError, ValueError, TypeError, KeyError):
        return (
            "Use only the verified claim ledger to write an English AI news feature. "
            "Separate facts from interpretation and cite direct sources inline."
        )


def _extract_markdown_urls(text):
    return re.findall(r"\]\((https?://[^)\s]+)", str(text or ""))


def _unsupported_urls(content, evidence):
    allowed = {canonical_url(source["url"]) for source in evidence["sources"]}
    return sorted({
        canonical_url(url)
        for url in _extract_markdown_urls(content)
        if canonical_url(url) not in allowed
    })


EXPECTED_NEWS_HEADINGS = (
    "## What actually happened?",
    "## How did an offline sandbox get out?",
    "## Why should you care?",
    "## What should teams do now?",
    "## What do we still not know?",
)

EXPECTED_NEWS_HEADINGS_KO = (
    "## 대체 무슨 일이 있었나?",
    "## 인터넷도 막았는데 어떻게 나갔을까?",
    "## 이게 우리한테 왜 중요할까?",
    "## 지금 바로 확인할 것",
    "## 아직 모르는 것",
)


def normalize_news_markdown(content, *, headings=EXPECTED_NEWS_HEADINGS):
    """구조화 JSON 안에서 개행이 공백으로 축약된 본문을 결정론적으로 복구한다."""
    content = str(content or "").replace("\\n", "\n").strip()
    for heading in headings:
        content = re.sub(
            rf"\s*{re.escape(heading)}\s*",
            f"\n\n{heading}\n\n",
            content,
        )
    # Mermaid 펜스는 반드시 독립된 줄이어야 Jekyll과 validator가 인식한다.
    content = re.sub(r"\s*```mermaid\s+", "\n\n```mermaid\n", content)
    content = re.sub(r";\s*```\s*", ";\n```\n\n", content)

    return re.sub(r"\n{3,}", "\n\n", content).strip()


def markdown_structure_errors(content):
    errors = []
    heading_count = len(re.findall(r"(?m)^##\s+\S", str(content or "")))
    if heading_count < 5:
        errors.append(f"독립된 H2 소제목 부족({heading_count}/5)")
    if re.search(r"(?<!\n)##\s+", str(content or "")):
        errors.append("본문 중간에 붙은 H2 소제목")
    if str(content or "").count("```") % 2:
        errors.append("코드 펜스 짝 불일치")
    return errors


def _extract_blocks(content, lang):
    pattern = re.compile(r"```" + lang + r"[ \t]*\n(.*?)```", re.S)
    return [(match.group(0), match.group(1)) for match in pattern.finditer(content)]


MERMAID_THEME = (
    '%%{init: {"theme":"base","themeVariables":{'
    '"primaryColor":"#F0EEE9","primaryBorderColor":"#2a78d6","primaryTextColor":"#2b2926",'
    '"secondaryColor":"#e8f0fb","secondaryBorderColor":"#4a3aa7","secondaryTextColor":"#2b2926",'
    '"tertiaryColor":"#eafaf3","tertiaryBorderColor":"#1baf7a","tertiaryTextColor":"#2b2926",'
    '"lineColor":"#8a8578","textColor":"#2b2926","edgeLabelBackground":"#F0EEE9",'
    '"fontFamily":"Pretendard, sans-serif"}}}%%'
)


def validate_mermaid(content):
    blocks = _extract_blocks(content, "mermaid")
    if not blocks:
        return content
    path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump([code.strip() for _, code in blocks], handle)
            path = handle.name
        result = subprocess.run(
            ["node", MERMAID_VALIDATOR, path],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        verdicts = json.loads(result.stdout)
        for (whole, _), verdict in zip(blocks, verdicts):
            if not verdict.get("ok", True):
                print(f"  Mermaid 제거: {str(verdict.get('error'))[:120]}")
                content = content.replace(whole, "", 1)
    except Exception as exc:
        print(f"  Mermaid 검증 건너뜀: {exc}")
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass
    return content


def apply_mermaid_theme(content):
    def replace(match):
        inner = match.group(1)
        if "%%{init" in inner:
            return match.group(0)
        return f"```mermaid\n{MERMAID_THEME}\n{inner.strip()}\n```"
    return re.sub(r"```mermaid[ \t]*\n(.*?)```", replace, content, flags=re.S)


EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF\U0000FE0F\U0000200D]"
)


def clean_text(value):
    return EMOJI_RE.sub("", str(value or "")).strip()


def fix_table_spacing(text):
    def is_row(line):
        return bool(re.match(r"^\s*\|.*\|", line))
    output = []
    for line in str(text or "").splitlines():
        if is_row(line) and output and output[-1].strip() and not is_row(output[-1]):
            output.append("")
        elif not is_row(line) and line.strip() and output and is_row(output[-1]):
            output.append("")
        output.append(line)
    return "\n".join(output)


def generate_blog_post(client, candidate, editorial, evidence):
    prompt = f"""{_load_system_prompt()}

[SELECTED STORY]
{json.dumps(candidate, ensure_ascii=False)}

[EDITORIAL DIRECTION]
{json.dumps(editorial, ensure_ascii=False)}

[VERIFIED CLAIM LEDGER — the only factual basis you may use]
{json.dumps(evidence, ensure_ascii=False)}

[PUBLISHING RULES]
- Write every output field in natural, globally readable English.
- Use only supported=true claims as facts and never use forbidden_claims.
- Preserve the conditions and status attached to every number, price, date, and
  availability statement.
- Place an inline [publisher or official source](URL) link next to the factual
  statement it supports.
- Invent no URL, number, capability, quotation, or user reaction outside the ledger.
- Open like a strong independent blogger talking to a smart friend: give the
  surprising consequence in the first two sentences, then explain it plainly.
- Use a warm, confident, conversational voice. Vary paragraph length, ask useful
  reader questions, use one concrete analogy when it genuinely clarifies the story,
  and make transitions feel natural rather than bureaucratic.
- Keep paragraphs short. Prefer vivid verbs and concrete nouns over report language
  such as "this event demonstrates" or "stakeholders should consider."
- The page renders key_takeaways as a three-line summary box above the article.
  Do not repeat that summary as a body section.
- Put the main searchable entity and verified change near the start of the title.
  No emoji, sensational punctuation, vague curiosity gaps, or clickbait.
- If an event occurred in a security evaluation or controlled test, say so in the
  title and opening. Use words such as "rogue," "out of control," or "stopped the
  attack" only when a direct source verifies exactly that state.
- description must be 120-160 characters. summary is 2-3 complete sentences.
- Write approximately 900-1,400 words without an H1, using only five useful H2
  sections. Every section must either explain the mechanism, answer why the reader
  should care, give an action, or mark an unresolved fact.
- Use these exact H2 headings in order: What actually happened? ->
  How did an offline sandbox get out? -> Why should you care? ->
  What should teams do now? -> What do we still not know?
- Make the first sentence under each major heading a stand-alone direct answer.
- Use a table or timeline only when it clarifies verified ledger facts.
- Use at most two Mermaid diagrams, only for a useful process or timeline. Never
  invent chart data.
- key_takeaways contains 3-5 independently quotable complete sentences.
- FAQ contains 3-4 direct answers of 2-4 sentences using only verified facts.
- tags contains 5-10 values and entities 3-10, preserving source spelling.
- The article will use images collected from verified source pages. Refer to
  visual evidence conservatively and never invent what an unseen image depicts.
"""
    post = generate_json(client, prompt, BLOG_SCHEMA, search=False, thinking="HIGH")
    content = normalize_news_markdown(clean_text(post.get("content")))
    content = fix_table_spacing(content.replace("\\n", "\n"))
    content = validate_mermaid(content)
    content = apply_mermaid_theme(content)
    structure_errors = markdown_structure_errors(content)
    if structure_errors:
        raise RuntimeError("마크다운 구조 검증 실패: " + " / ".join(structure_errors))
    unsupported = _unsupported_urls(content, evidence)
    if unsupported:
        raise RuntimeError("본문에 claim ledger 밖 URL이 포함됨: " + ", ".join(unsupported[:5]))
    post["content"] = content
    post["title"] = clean_text(post.get("title"))
    if not post["title"]:
        raise RuntimeError("English title is missing")
    post["description"] = clean_text(post.get("description"))
    post["summary"] = clean_text(post.get("summary"))
    if not 80 <= len(post["description"]) <= 180:
        raise RuntimeError(
            f"메타 설명 길이 부적합: {len(post['description'])}자 (허용 80~180자)"
        )
    post["tags"] = list(dict.fromkeys(clean_text(value) for value in post.get("tags") or [] if clean_text(value)))[:10]
    post["entities"] = list(dict.fromkeys(
        [clean_text(value) for value in post.get("entities") or [] if clean_text(value)]
        + [clean_text(value) for value in candidate.get("entities") or [] if clean_text(value)]
    ))[:12]
    post["key_takeaways"] = [
        clean_text(value) for value in post.get("key_takeaways") or [] if clean_text(value)
    ][:5]
    post["faq"] = [
        {"question": clean_text(item.get("question")), "answer": clean_text(item.get("answer"))}
        for item in post.get("faq") or []
        if clean_text(item.get("question")) and clean_text(item.get("answer"))
    ][:6]
    if len(post["faq"]) < 3 or len(post["key_takeaways"]) < 3:
        raise RuntimeError("AEO 출고 규칙 미달: FAQ 또는 핵심 요약 부족")
    return post


def generate_korean_version(client, english_post, evidence):
    """Create a fact-locked Korean counterpart for the English master article."""
    prompt = f"""You are OPSOAI's Korean technology editor. Localize the supplied
English article into clear, natural Korean for Korean developers, operators,
founders, creators, policymakers, and everyday AI users.

[ENGLISH MASTER — translate this, do not independently rewrite the facts]
{json.dumps(english_post, ensure_ascii=False)}

[VERIFIED CLAIM LEDGER — use it only to prevent translation drift]
{json.dumps(evidence, ensure_ascii=False)}

[NON-NEGOTIABLE]
- Translate every reader-facing field into Korean: title, description, summary,
  content, key_takeaways, FAQ, and general-topic tags.
- Preserve company, product, model, benchmark, and person names exactly as written
  by their sources. Preserve every number, date, status condition, and uncertainty.
- Keep every Markdown source URL byte-for-byte identical to the English master.
- Add no fact, inference, quote, number, reaction, or URL.
- Keep Mermaid node meaning faithful; translate labels only when safe.
- Preserve the lively independent-blogger voice rather than translating into formal
  corporate Korean. Use natural endings such as "~입니다" and occasional "~죠" or
  "~볼까요?" where they fit, without becoming flippant.
- Keep paragraphs short, transitions conversational, and one concrete analogy when
  it helps. Avoid repetitive report phrases such as "시사한다" and "주목할 필요가 있다."
- The page renders key_takeaways in a separate three-line summary box. Do not add
  a summary section to content.
- Use these exact five H2 headings in order:
  대체 무슨 일이 있었나? -> 인터넷도 막았는데 어떻게 나갔을까? ->
  이게 우리한테 왜 중요할까? -> 지금 바로 확인할 것 -> 아직 모르는 것.
- Do not use an H1, emoji, clickbait, vague curiosity gaps, or sensational wording.
- description should be a natural 70-160 Korean-character search description.
- Keep key_takeaways at 3-5 items and FAQ at 3-4 items.
- Return the same JSON shape as the English master.
"""
    post = generate_json(client, prompt, BLOG_SCHEMA, search=False, thinking="HIGH")
    content = normalize_news_markdown(
        clean_text(post.get("content")),
        headings=EXPECTED_NEWS_HEADINGS_KO,
    )
    content = fix_table_spacing(content.replace("\\n", "\n"))
    content = validate_mermaid(content)
    content = apply_mermaid_theme(content)
    structure_errors = markdown_structure_errors(content)
    if structure_errors:
        raise RuntimeError("한국어판 마크다운 구조 검증 실패: " + " / ".join(structure_errors))
    unsupported = _unsupported_urls(content, evidence)
    if unsupported:
        raise RuntimeError(
            "한국어판에 claim ledger 밖 URL이 포함됨: " + ", ".join(unsupported[:5])
        )
    english_urls = set(_extract_markdown_urls(english_post["content"]))
    korean_urls = set(_extract_markdown_urls(content))
    if english_urls != korean_urls:
        raise RuntimeError("한국어판의 직접 출처 URL이 영어판과 일치하지 않습니다")

    post["content"] = content
    for key in ("title", "description", "summary"):
        post[key] = clean_text(post.get(key))
        if not post[key]:
            raise RuntimeError(f"한국어판 {key} 필드가 비어 있습니다")
    if not 60 <= len(post["description"]) <= 180:
        raise RuntimeError(
            f"한국어 메타 설명 길이 부적합: {len(post['description'])}자 (허용 60~180자)"
        )
    post["tags"] = list(dict.fromkeys(
        clean_text(value) for value in post.get("tags") or [] if clean_text(value)
    ))[:10]
    # Entity spellings must remain canonical across the language pair.
    post["entities"] = list(english_post["entities"])
    post["key_takeaways"] = [
        clean_text(value) for value in post.get("key_takeaways") or [] if clean_text(value)
    ][:5]
    post["faq"] = [
        {
            "question": clean_text(item.get("question")),
            "answer": clean_text(item.get("answer")),
        }
        for item in post.get("faq") or []
        if clean_text(item.get("question")) and clean_text(item.get("answer"))
    ][:6]
    if len(post["key_takeaways"]) < 3 or len(post["faq"]) < 3:
        raise RuntimeError("한국어판 핵심 요약 또는 FAQ 개수가 부족합니다")
    return post


def editorial_for_candidate(editorial, candidate):
    """선택 1순위의 근거가 막혔을 때 다른 뉴스에 이전 각도를 잘못 씌우지 않는다."""
    if candidate.get("ref") == editorial.get("selected_ref"):
        return editorial
    return {
        **editorial,
        "selected_ref": candidate.get("ref"),
        "news_angle": str(candidate.get("why_it_matters") or candidate.get("headline") or ""),
        "reader_question": (
            f"What materially changes because of the {candidate.get('topic_name')} announcement?"
        ),
        "why_now": (
            f"The change was published on {candidate.get('published_at')}; readers need to "
            "verify its availability and practical impact now."
        ),
        "practical_impact": str(candidate.get("why_it_matters") or ""),
        "risks": ["Fallback story selected after the first candidate failed evidence checks"],
    }


def _safe_slug(value):
    value = unicodedata.normalize("NFKD", str(value or "AI-News"))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return (value or "AI-News")[:110]


def _card_font(size, *, bold=False):
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    order = candidates if bold else tuple(reversed(candidates))
    for path in order:
        if os.path.isfile(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _wrap_card_title(draw, value, font, max_width, max_lines=3):
    words = str(value or "AI News").split()
    lines = []
    current = ""
    for word in words:
        proposed = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), proposed, font=font)[2]
        if current and width > max_width:
            lines.append(current)
            current = word
        else:
            current = proposed
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = textwrap.shorten(lines[-1], width=34, placeholder="...")
    return lines


def _draw_wrapped_text(
    draw,
    value,
    *,
    xy,
    font,
    max_width,
    fill,
    max_lines,
    line_height,
):
    lines = _wrap_card_title(draw, value, font, max_width, max_lines=max_lines)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += line_height
    return y


def create_news_social_card(post, *, now=None, show_date=True):
    """Create one fallback cover only when sources provide no usable image."""
    now = now or kst_now()
    slug = _safe_slug(post.get("title"))[:72]
    filename = f"{now:%Y-%m-%d}-{slug}.png"
    os.makedirs(NEWS_IMAGES_DIR, exist_ok=True)
    path = os.path.join(NEWS_IMAGES_DIR, filename)

    canvas = Image.new("RGB", (1200, 630), "#07111F")
    draw = ImageDraw.Draw(canvas)
    for y in range(630):
        ratio = y / 629
        draw.line(
            (0, y, 1200, y),
            fill=(
                int(7 + 7 * ratio),
                int(17 + 16 * ratio),
                int(31 + 22 * ratio),
            ),
        )
    draw.ellipse((850, -160, 1320, 310), fill="#123E68")
    draw.ellipse((930, 340, 1250, 660), fill="#145A5C")
    draw.rounded_rectangle((72, 58, 206, 192), radius=24, fill="#F5F7FA")
    if os.path.isfile(LOGO_PATH):
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo.thumbnail((104, 104), Image.Resampling.LANCZOS)
        canvas.paste(logo, (87, 73), logo)

    brand_font = _card_font(28, bold=True)
    title_font = _card_font(53, bold=True)
    label_font = _card_font(22, bold=True)
    small_font = _card_font(20)
    draw.text((230, 70), "OPSOAI", fill="#F8FAFC", font=brand_font)
    draw.text((230, 112), "VERIFIED AI INTELLIGENCE", fill="#62D7D2", font=label_font)
    draw.rounded_rectangle((72, 232, 320, 278), radius=22, fill="#2A78D6")
    draw.text((94, 241), "THE STORY TO KNOW", fill="#FFFFFF", font=small_font)

    title_lines = _wrap_card_title(
        draw, post.get("title"), title_font, max_width=880, max_lines=4
    )
    y = 310
    for line in title_lines:
        draw.text((72, y), line, fill="#F8FAFC", font=title_font)
        y += 63
    footer = (
        now.strftime("%B %d, %Y  •  opsoai.com")
        if show_date
        else "GLOBAL AI NEWS  •  opsoai.com"
    )
    draw.text((72, 580), footer, fill="#B8C5D6", font=small_font)
    canvas.save(path, format="PNG", optimize=True)
    return {
        "path": f"/assets/img/news/{filename}",
        "alt": f"Editorial cover for {post.get('title')}",
        "caption": "Fallback editorial cover created by OPSOAI.",
        "credit": "OPSOAI",
        "generated": True,
        "width": 1200,
        "height": 630,
    }


def _save_source_image(candidate, source, post, *, now):
    image_url = candidate["url"]
    if not _safe_remote_url(image_url):
        raise ValueError("image URL is not public HTTPS")
    response = _safe_streaming_get(
        image_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/avif,image/webp,image/png,image/jpeg,image/gif",
        },
    )
    try:
        response.raise_for_status()
        final_url = response.url
        if not response.headers.get("content-type", "").lower().startswith("image/"):
            raise ValueError("remote asset is not an image")
        payload = _bounded_response_bytes(response, limit=8 * 1024 * 1024)
    finally:
        response.close()
    with Image.open(BytesIO(payload)) as inspected:
        inspected.verify()
    with Image.open(BytesIO(payload)) as inspected:
        width, height = inspected.size
        image_format = (inspected.format or "").upper()
    extensions = {
        "JPEG": "jpg",
        "PNG": "png",
        "WEBP": "webp",
        "GIF": "gif",
    }
    if image_format not in extensions:
        raise ValueError(f"unsupported source image format: {image_format}")
    if width < 600 or height < 315:
        raise ValueError(f"source image is too small: {width}x{height}")

    publisher = str(source.get("publisher") or "Source").strip()
    article_title = str(source.get("title") or post.get("title") or "AI news").strip()
    filename = (
        f"{now:%Y-%m-%d}-{_safe_slug(post.get('title'))[:50]}-"
        f"{_safe_slug(publisher)[:24]}-"
        f"{hashlib.sha256(canonical_url(source.get('url')).encode()).hexdigest()[:8]}"
        f"-source.{extensions[image_format]}"
    )
    os.makedirs(NEWS_IMAGES_DIR, exist_ok=True)
    local_path = os.path.join(NEWS_IMAGES_DIR, filename)
    temporary = f"{local_path}.tmp"
    try:
        with open(temporary, "xb") as handle:
            handle.write(payload)
        os.replace(temporary, local_path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    declared_alt = str(candidate.get("alt") or "").strip()
    alt = declared_alt or f"Source image for {article_title} from {publisher}"
    return {
        "path": f"/assets/img/news/{filename}",
        "alt": alt[:240],
        "caption": f"Image published with “{article_title}.”",
        "credit": publisher,
        "source_url": canonical_url(source.get("url")),
        "original_url": canonical_url(final_url),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "width": width,
        "height": height,
    }


def collect_source_images(post, evidence, *, now=None, limit=3):
    """Collect one declared share image per checked source, official sources first."""
    if os.environ.get("AI_NEWS_COLLECT_SOURCE_IMAGES", "1").lower() in {"0", "false", "no"}:
        return []
    now = now or kst_now()
    sources = sorted(
        evidence.get("sources", []),
        key=lambda source: 0 if source.get("tier") == "official" else 1,
    )
    images = []
    seen_urls = set()
    seen_hashes = set()
    for source in sources:
        if len(images) >= limit:
            break
        try:
            candidates = source_image_metadata(source)
        except Exception as exc:
            print(f"  이미지 메타데이터 수집 생략 ({source.get('publisher')}): {exc}")
            continue
        for candidate in candidates:
            normalized = canonical_url(candidate["url"])
            if not normalized or normalized in seen_urls:
                continue
            seen_urls.add(normalized)
            try:
                image = _save_source_image(candidate, source, post, now=now)
            except Exception as exc:
                print(f"  출처 이미지 생략 ({source.get('publisher')}): {exc}")
                continue
            if image["sha256"] in seen_hashes:
                try:
                    os.unlink(os.path.join(
                        NEWS_IMAGES_DIR, os.path.basename(image["path"])
                    ))
                except OSError:
                    pass
                continue
            seen_hashes.add(image.pop("sha256"))
            images.append(image)
            break
    return images


def _visual_figure(image, *, lang="en"):
    alt = html.escape(image["alt"], quote=True)
    caption = html.escape(image.get("caption") or "Source image")
    credit = html.escape(image.get("credit") or "Source")
    source_url = html.escape(image.get("source_url") or "", quote=True)
    is_korean = str(lang).lower().startswith("ko")
    credit_label = "출처" if is_korean else "Credit"
    figure_label = "출처 이미지" if is_korean else "Source image"
    credit_html = (
        f' <a href="{source_url}" rel="noopener noreferrer" target="_blank">'
        f"{credit_label}: {credit}</a>"
        if source_url
        else f" {credit_label}: {credit}"
    )
    return (
        '<figure class="news-visual">\n'
        f'  <img src="{image["path"]}" alt="{alt}" '
        f'width="{image["width"]}" height="{image["height"]}" '
        'loading="lazy" decoding="async">\n'
        f"  <figcaption><strong>{figure_label}</strong> — {caption}{credit_html}</figcaption>\n"
        "</figure>"
    )


def insert_source_images(content, images, *, lang="en"):
    """Distribute collected source visuals through the article body."""
    if str(lang).lower().startswith("ko"):
        targets = (
            "## 이게 우리한테 왜 중요할까?",
            "## 지금 바로 확인할 것",
            "## 아직 모르는 것",
        )
    else:
        targets = (
            "## Why should you care?",
            "## What should teams do now?",
            "## What do we still not know?",
        )
    for target, image in zip(targets, images):
        content = content.replace(
            target,
            f"{_visual_figure(image, lang=lang)}\n\n{target}",
            1,
        )
    return content


def _localized_images(image, article_images, *, lang, title):
    if not str(lang).lower().startswith("ko"):
        return dict(image), [dict(item) for item in article_images]

    def localize(item):
        localized = dict(item)
        credit = str(item.get("credit") or "원문 출처")
        localized["alt"] = f"{credit} 원문에 게시된 ‘{title}’ 관련 이미지"
        localized["caption"] = f"{credit}가 원문과 함께 게시한 이미지입니다."
        return localized

    return localize(image), [localize(item) for item in article_images]


def save_post(
    post,
    candidate,
    editorial,
    evidence,
    *,
    now=None,
    lang="en",
    story_slug=None,
    translations=None,
    image=None,
    article_images=None,
):
    now = now or kst_now()
    story_slug = (story_slug or _safe_slug(post.get("title"))).lower()
    is_korean = str(lang).lower().startswith("ko")
    filename_slug = f"{story_slug}-ko" if is_korean else story_slug
    filename = f"{now:%Y-%m-%d}-{filename_slug}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    if os.path.exists(filepath):
        raise RuntimeError(f"같은 파일이 이미 존재합니다: {filename}")
    os.makedirs(POSTS_DIR, exist_ok=True)
    source_urls = [source["url"] for source in evidence["sources"]]
    if image is None:
        collected_images = collect_source_images(post, evidence, now=now)
        if collected_images:
            image = collected_images[0]
            article_images = collected_images[1:]
        else:
            print("  사용 가능한 출처 이미지가 없어 커버 1장을 생성합니다")
            image = create_news_social_card(post, now=now)
            article_images = []
    article_images = article_images or []
    image, article_images = _localized_images(
        image,
        article_images,
        lang=lang,
        title=post["title"],
    )
    content = insert_source_images(post["content"], article_images, lang=lang)
    front_matter = {
        "layout": "post",
        "title": post["title"],
        "date": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "last_modified_at": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "lang": "ko-KR" if is_korean else "en",
        "permalink": f"/{'ko' if is_korean else 'en'}/news/{story_slug}/",
        "translation_key": story_slug,
        "categories": ["AI News"],
        "tags": post["tags"],
        "description": post["description"],
        "summary": post["summary"],
        "author": "OPSOAI",
        "article_type": "NewsArticle",
        "image": image,
        "news_source_url": candidate["source_url"],
        "news_published_at": candidate["published_at"],
        "source_citations": [
            {
                "name": source["publisher"],
                "url": source["url"],
                "published_at": source["published_at"],
            }
            for source in evidence["sources"]
        ],
        "entities": post["entities"],
        "key_takeaways": post["key_takeaways"],
        "faq": post["faq"],
        "editorial": {
            "angle": editorial["news_angle"],
            "reader_question": editorial["reader_question"],
        },
        "sitemap": True,
    }
    if translations:
        front_matter["translations"] = translations
    if article_images:
        front_matter["article_images"] = article_images
    if "```mermaid" in content:
        front_matter["mermaid"] = True

    body = [content.rstrip()]
    body += ["", "## 많이 묻는 질문" if is_korean else "## People are asking", ""]
    for item in post["faq"]:
        body += [f"### {item['question']}", "", item["answer"], ""]
    body += ["## 확인한 원문" if is_korean else "## Sources we checked", ""]
    for source in evidence["sources"]:
        body.append(
            f"- [{source['publisher']} — {source['title']}]({source['url']})"
            f" ({source['published_at']})"
        )
    if is_korean:
        body += [
            "",
            "> 이 글은 위 원문을 직접 확인해 작성했습니다. 가격, 지역별 제공 범위, "
            "기능 범위는 게시 후 달라질 수 있으므로 도입이나 구매 결정 전 공식 "
            "문서를 다시 확인하세요.",
            "",
        ]
    else:
        body += [
            "",
            "> This article was prepared from the direct sources above. Pricing, regional "
            "availability, and feature scope may change after publication; verify the "
            "official documentation before making a deployment or purchasing decision.",
            "",
        ]

    temporary = f"{filepath}.tmp"
    try:
        with open(temporary, "x", encoding="utf-8") as handle:
            handle.write("---\n")
            yaml.safe_dump(front_matter, handle, allow_unicode=True, sort_keys=False, width=1000)
            handle.write("---\n\n")
            handle.write("\n".join(body))
        os.replace(temporary, filepath)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"저장 완료: {filepath}")
    print(f"검증 출처 {len(source_urls)}개 / supported claim "
          f"{sum(1 for claim in evidence['claims'] if claim['supported'])}개")
    return filepath


def save_bilingual_posts(
    english_post,
    korean_post,
    candidate,
    editorial,
    evidence,
    *,
    now=None,
):
    """Save one fact-checked story as linked English and Korean editions."""
    now = now or kst_now()
    story_slug = _safe_slug(english_post.get("title")).lower()
    translations = {
        "en": f"/en/news/{story_slug}/",
        "ko": f"/ko/news/{story_slug}/",
    }
    collected_images = collect_source_images(english_post, evidence, now=now)
    if collected_images:
        image = collected_images[0]
        article_images = collected_images[1:]
    else:
        print("  사용 가능한 출처 이미지가 없어 공용 커버 1장을 생성합니다")
        image = create_news_social_card(english_post, now=now)
        article_images = []

    paths = []
    for post, lang in ((english_post, "en"), (korean_post, "ko-KR")):
        paths.append(save_post(
            post,
            candidate,
            editorial,
            evidence,
            now=now,
            lang=lang,
            story_slug=story_slug,
            translations=translations,
            image=image,
            article_images=article_images,
        ))
    return paths


def main():
    client = get_client()
    preflight_check(client)
    now = kst_now()
    history = recent_post_history()

    print(f"\n[1/5] 최신 AI 뉴스 후보 수집 ({now:%Y-%m-%d %H:%M KST})")
    candidates = discover_news_candidates(client, now=now, history=history)
    if not candidates:
        raise RuntimeError("신선하고 중복되지 않은 AI 뉴스 후보를 찾지 못했습니다")
    print(f"  검증 가능한 후보 {len(candidates)}건")

    print("[2/5] 편집장 선정")
    editorial = select_editorial_topic(client, candidates, history)
    selected_ref = editorial["selected_ref"]
    ordered = sorted(candidates, key=lambda item: item["ref"] != selected_ref)

    errors = []
    for candidate in ordered[:4]:
        try:
            current_editorial = editorial_for_candidate(editorial, candidate)
            print(f"  선택 시도: {candidate['headline']}")
            print("[3/5] 독립 claim ledger 팩트체크")
            evidence = build_evidence_pack(client, candidate, current_editorial, now=now)
            print("[4/5] 영어 SEO/AEO/GEO 기사 작성")
            english_post = generate_blog_post(client, candidate, current_editorial, evidence)
            print("[5/5] 사실 고정 한국어판 작성 및 언어 쌍 저장")
            korean_post = generate_korean_version(client, english_post, evidence)
            return save_bilingual_posts(
                english_post,
                korean_post,
                candidate,
                current_editorial,
                evidence,
                now=now,
            )
        except Exception as exc:
            errors.append(f"{candidate.get('headline')}: {exc}")
            print(f"  후보 출고 중단: {exc}")
    raise RuntimeError("상위 후보 모두 출고 검증 실패 / " + " / ".join(errors))


if __name__ == "__main__":
    main()
