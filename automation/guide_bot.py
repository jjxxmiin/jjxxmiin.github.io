#!/usr/bin/env python3
"""검색 수요가 확인된 주제로 실용 가이드를 발행한다.

왜 만들었나
    612편을 쓰고도 하루 검색 세션이 4.4였다. Search Console을 보면 순위는
    좋은데(1페이지 5위) 노출 자체가 없다. 아무도 안 찾는 말로 글을 써 온 것이다.
    이 봇은 구글과 네이버 자동완성으로 수요를 확인한 주제만 골라 쓴다.

무엇을 쓰나
    automation/data/topic_queue.json 의 대기 주제 중 우선순위가 가장 높은 하나.
    '클로드 요금제 비교'처럼 사람들이 돈 쓰기 직전에 치는 질의를 노린다.
    변형 키워드는 소제목으로 흡수해 한 편이 클러스터 전체를 커버하게 만든다.

    python automation/guide_bot.py                # 다음 주제 발행
    python automation/guide_bot.py --dry-run      # 생성만 하고 저장 안 함
    python automation/guide_bot.py --topic-id 로컬-llm
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import tempfile

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.genai import types  # noqa: E402

import daily_trend_bot as base  # noqa: E402
from glossary import insert_box as insert_glossary_box  # noqa: E402
from apply_tags import tags_for  # noqa: E402
from make_thumbnail import generate_card  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "automation", "data", "topic_queue.json")
LEDGER = os.path.join(ROOT, "automation", "data", "written_topics.json")
POSTS_DIR = os.path.join(ROOT, "_posts")
AUTOMATION_TAG = "keyword_guide"

# 사실을 모아 오는 단계. 근거 없이 쓰면 가격 같은 건 바로 틀린다.
RESEARCH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "facts": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "text": {"type": "STRING"},
                    "source_url": {"type": "STRING"},
                    "source_name": {"type": "STRING"},
                    "source_tier": {"type": "STRING"},
                },
                "required": ["text", "source_url", "source_name", "source_tier"],
            },
        },
        "unknowns": {"type": "ARRAY", "items": {"type": "STRING"}},
        "volatile": {"type": "BOOLEAN"},
    },
    "required": ["facts", "unknowns", "volatile"],
}

POST_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title_korean": {"type": "STRING"},
        "title_english": {"type": "STRING"},
        "description": {"type": "STRING"},
        "summary": {"type": "STRING"},
        "content": {"type": "STRING"},
        "faq": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"question": {"type": "STRING"}, "answer": {"type": "STRING"}},
                "required": ["question", "answer"],
            },
        },
    },
    "required": ["title_korean", "title_english", "description", "summary", "content", "faq"],
}


_SPACE = re.compile(r"\s+")
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_NON_PROSE_HTML = re.compile(
    r"<(script|style|pre|code|svg|canvas)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
# 실제 HTML 요소 이름만 허용한다. 임의의 영문자까지 태그로 보면 ``y_{<t}`` 같은
# 수식이 뒤의 ``>``를 만날 때까지 본문을 삼키므로, 알려진 요소를 화이트리스트한다.
_HTML_ELEMENTS = (
    "a|abbr|address|article|aside|audio|b|blockquote|body|br|button|caption|"
    "cite|col|colgroup|dd|del|details|dfn|dialog|div|dl|dt|em|figcaption|"
    "figure|footer|form|h1|h2|h3|h4|h5|h6|head|header|hr|html|i|iframe|"
    "img|input|ins|kbd|label|li|link|main|mark|meta|nav|noscript|ol|optgroup|"
    "option|p|picture|q|s|samp|section|select|small|source|span|strong|sub|"
    "summary|sup|table|tbody|td|template|textarea|tfoot|th|thead|time|title|"
    "tr|u|ul|var|video|wbr"
)
_HTML_TAG = re.compile(
    rf"</?(?:{_HTML_ELEMENTS})\b(?:\"[^\"]*\"|'[^']*'|[^'\">])*?>",
    re.IGNORECASE | re.DOTALL,
)
_LIQUID = re.compile(r"\{[%{].*?[}%]\}", re.DOTALL)
_LINK_DEFINITION = re.compile(r"(?m)^[ \t]{0,3}\[[^]\n]+\]:[ \t]+\S+.*$")
_KRAMDOWN_ATTRIBUTE = re.compile(r"\{:[^}\n]+\}")
_ATX_HEADING = re.compile(
    r"(?m)^[ \t]{0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$"
)
_SETEXT_HEADING = re.compile(
    r"(?m)^[ \t]{0,3}(?![#>|])(?P<text>\S[^\n]*)\n"
    r"[ \t]{0,3}(?P<underline>=+|-+)[ \t]*$"
)
_HTML_HEADING = re.compile(r"<h([1-6])\b[^>]*>", re.IGNORECASE)
_GENERIC_HERO_ALT = {"paper thumbnail", "preview image", "thumbnail"}
# Keep these expressions in lockstep with tools/audit_content_quality.py.  The
# generated guide must fail while the workflow can still retry generation, not
# after it has already written a post and reached the repository-wide audit.
_HYPE = re.compile(
    r"(게임\s*체인저|충격적(?:인|으로)?|미친\s*(?:성능|도구|프로젝트)|"
    r"무조건\s*(?:써|사|도입)|직접\s+(?:써|사용해|테스트해)\s*보니|"
    r"왜\s*(?:이제야|아무도).*알려|개발자\s*직업이\s*위험)",
    re.IGNORECASE,
)
_FALSE_EXPERIENCE = re.compile(
    r"(10년\s*차\s*(?:시니어|엔지니어|개발자)|"
    r"시니어\s*엔지니어로서\s*단언|"
    r"제가\s+(?:직접|최근|현업)|"
    r"직접\s+(?:써|사용해|테스트해)\s*보니)",
    re.IGNORECASE,
)
_TITLE_HYPE = re.compile(
    r"(게임.?체인저|충격|미친|궁극의|치명적\s*민낯|\b민낯\b|"
    r"(?:기술|도구|직업|패턴|엔지니어링)의\s*종말|끝났다\??|"
    r"집어삼|뒤집어엎|멱살을\s*잡|구원일까|재앙일까|"
    r"10년\s*차|왜.*(?:이제야|뒤늦게|몰랐)|"
    r"honest\s+review|game.?changer|insane|shocking|ultimate|"
    r"\b(?:salvation|disaster)\b|[\U0001F300-\U0001FAFF])",
    re.IGNORECASE,
)
_DECORATIVE_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
_KEYCAP = re.compile(r"[0-9]\ufe0f?\u20e3")


def _strip_fenced_blocks(markdown: str) -> tuple[str, bool]:
    """코드 펜스를 줄 단위로 제거하고 닫히지 않은 펜스 여부도 돌려준다.

    단순한 비탐욕 정규식은 물결표 펜스, CRLF, 펜스 길이가 다른 경우를 놓치기 쉽다.
    줄 스캐너를 쓰면 코드 속 마크다운과 장문의 다이어그램이 본문 분량이나 제목
    계층에 섞이지 않는다.
    """
    kept: list[str] = []
    fence_char: str | None = None
    fence_len = 0
    opening = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
    for line in str(markdown or "").splitlines(keepends=True):
        if fence_char is None:
            match = opening.match(line)
            if match:
                marker = match.group(1)
                fence_char, fence_len = marker[0], len(marker)
                kept.append("\n" if line.endswith(("\n", "\r")) else "")
                continue
            kept.append(line)
            continue

        candidate = line.strip()
        indent = len(line) - len(line.lstrip(" \t"))
        is_closing = (
            indent <= 3
            and len(candidate) >= fence_len
            and candidate
            and set(candidate) == {fence_char}
        )
        if is_closing:
            fence_char, fence_len = None, 0
        kept.append("\n" if line.endswith(("\n", "\r")) else "")
    return "".join(kept), fence_char is None


def _find_balanced(text: str, start: int, opening: str, closing: str) -> int:
    """Return the matching delimiter index, respecting escapes and nesting."""
    depth = 0
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _strip_markdown_images(text: str) -> str:
    """이미지 대체문과 목적지를 함께 제거한다 (중첩 괄호 URL 포함)."""
    output: list[str] = []
    index = 0
    while index < len(text):
        if not text.startswith("![", index):
            output.append(text[index])
            index += 1
            continue
        label_end = _find_balanced(text, index + 1, "[", "]")
        if label_end < 0:
            output.append(text[index])
            index += 1
            continue
        end = label_end + 1
        if end < len(text) and text[end] == "(":
            destination_end = _find_balanced(text, end, "(", ")")
            end = destination_end + 1 if destination_end >= 0 else end
        elif end < len(text) and text[end] == "[":
            reference_end = _find_balanced(text, end, "[", "]")
            end = reference_end + 1 if reference_end >= 0 else end
        output.append(" ")
        index = end
    return "".join(output)


def _replace_markdown_links(text: str) -> str:
    """링크 목적지는 빼고 실제 화면에 보이는 라벨만 남긴다."""
    output: list[str] = []
    index = 0
    while index < len(text):
        if text[index] != "[" or (index and text[index - 1] == "!"):
            output.append(text[index])
            index += 1
            continue
        label_end = _find_balanced(text, index, "[", "]")
        if label_end < 0:
            output.append(text[index])
            index += 1
            continue
        end = label_end + 1
        linked = False
        if end < len(text) and text[end] == "(":
            destination_end = _find_balanced(text, end, "(", ")")
            if destination_end >= 0:
                end, linked = destination_end + 1, True
        elif end < len(text) and text[end] == "[":
            reference_end = _find_balanced(text, end, "[", "]")
            if reference_end >= 0:
                end, linked = reference_end + 1, True
        if linked:
            output.append(text[index + 1:label_end])
            index = end
        else:
            output.append(text[index])
            index += 1
    return "".join(output)


def _structural_text(markdown: str) -> tuple[str, bool]:
    text, balanced = _strip_fenced_blocks(markdown)
    text = _HTML_COMMENT.sub(" ", text)
    text = _NON_PROSE_HTML.sub(" ", text)
    return text, balanced


def _visible_text(markdown: str) -> str:
    """렌더링되는 설명문만 남긴다. Markdown 문법 자체는 분량에 넣지 않는다."""
    text, _ = _structural_text(markdown)
    text = _LIQUID.sub(" ", text)
    text = _strip_markdown_images(text)
    text = _LINK_DEFINITION.sub(" ", text)
    text = _replace_markdown_links(text)
    text = _HTML_TAG.sub(" ", text)
    text = html.unescape(text)
    text = re.sub(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+", "", text)
    text = re.sub(r"(?m)^[ \t]{0,3}(?:=+|-+)[ \t]*$", " ", text)
    text = re.sub(r"(?m)^[ \t]*(?:[-*+] |\d+[.)][ \t]+|>[ \t]?)", "", text)
    text = _KRAMDOWN_ATTRIBUTE.sub(" ", text)
    text = re.sub(r"\\([\\`*{}\[\]()#+.!_>~-])", r"\1", text)
    text = re.sub(r"[`*_~|]", " ", text)
    return _SPACE.sub(" ", text).strip()


def _heading_entries(markdown: str) -> tuple[list[tuple[int, int, str, str]], bool]:
    """ATX, Setext, raw HTML 제목을 문서 순서와 문법 종류까지 읽는다."""
    text, balanced = _structural_text(markdown)
    entries: list[tuple[int, int, str, str]] = []
    for match in _ATX_HEADING.finditer(text):
        entries.append((match.start(), len(match.group(1)), match.group(2).strip(), "atx"))
    for match in _SETEXT_HEADING.finditer(text):
        level = 1 if match.group("underline").startswith("=") else 2
        entries.append((match.start(), level, match.group("text").strip(), "setext"))
    for match in _HTML_HEADING.finditer(text):
        entries.append((match.start(), int(match.group(1)), "HTML heading", "html"))
    entries.sort(key=lambda item: item[0])
    return entries, balanced


def _intro_text(markdown: str) -> str:
    text, _ = _structural_text(markdown)
    headings, _ = _heading_entries(markdown)
    intro = text[:headings[0][0]] if headings else text
    return _visible_text(intro)


def _metadata_and_style_errors(front_matter: dict, body: str) -> list[str]:
    """Mirror repository-wide metadata and honesty checks before publication."""
    errors: list[str] = []
    title = _SPACE.sub(" ", str(front_matter.get("title") or "")).strip()
    summary = _SPACE.sub(" ", str(front_matter.get("summary") or "")).strip()
    description = _SPACE.sub(
        " ", str(front_matter.get("description") or summary)
    ).strip()

    if not title:
        errors.append("제목 누락")
    elif title.startswith("[") or _TITLE_HYPE.search(title):
        match = _TITLE_HYPE.search(title)
        reason = match.group(0) if match else "대괄호 접두어"
        errors.append(f"낚시성 또는 허위 경험 제목 표현: {reason}")
    if not summary:
        errors.append("요약 누락")
    if not 80 <= len(description) <= 160:
        errors.append(f"메타 설명 길이 부적합: {len(description)}자")

    plain = _visible_text(body)
    style_text = " ".join((title, summary, description, plain))
    hype = _HYPE.search(style_text)
    if hype:
        # The global audit reports this as a warning, but the workflow runs it with
        # --warnings-as-errors.  Treating it as an error here gives generation a retry.
        errors.append(f"과장 또는 허위 경험 문구: {hype.group(0)}")
    false_experience = _FALSE_EXPERIENCE.search(style_text)
    if false_experience:
        errors.append(f"근거 없는 1인칭 경험 문구: {false_experience.group(0)}")

    outside_fences, _ = _strip_fenced_blocks(body)
    emoji_count = len(_DECORATIVE_EMOJI.findall(outside_fences))
    if emoji_count > 5:
        errors.append(f"장식용 이모지 과다: {emoji_count}개")
    if _KEYCAP.search(outside_fences):
        errors.append("장식용 키캡 숫자 포함")
    return errors


def _generated_post_errors(post: object) -> list[str]:
    """Validate model fields immediately so the workflow can regenerate them."""
    if not isinstance(post, dict):
        return ["생성 결과가 객체가 아님"]
    title_english = _SPACE.sub(
        " ", str(post.get("title_english") or "")
    ).strip()
    errors = _metadata_and_style_errors(
        {
            "title": base.strip_emojis(str(post.get("title_korean") or "")).strip(),
            "summary": base.strip_emojis(str(post.get("summary") or "")).strip(),
            "description": base.strip_emojis(
                str(post.get("description") or "")
            ).strip(),
        },
        base.strip_emojis(str(post.get("content") or "")),
    )
    if not title_english:
        errors.append("파일명용 영문 제목 누락")
    return list(dict.fromkeys(errors))


def _validate_generated_post(post: object) -> None:
    errors = _generated_post_errors(post)
    if errors:
        raise ValueError("생성 글 메타/문체 검증 실패: " + "; ".join(errors))


def _guide_quality_errors(
    front_matter: dict,
    article_content: str,
    full_body: str,
    *,
    require_hero: bool,
) -> list[str]:
    """발행 직전 가이드를 전역 콘텐츠 감사와 같은 기준 이상으로 검사한다.

    분량과 구조는 FAQ·출처로 부풀릴 수 없는 핵심 본문에서 검사하고, FAQ는 실제로
    붙인 최종 본문에서 다시 대조한다.
    """
    errors: list[str] = []
    errors.extend(_metadata_and_style_errors(front_matter, full_body))

    plain = _visible_text(article_content)
    visible_length = len(re.sub(r"\s", "", plain))
    if visible_length < 3_500:
        errors.append(f"실제 설명문이 너무 짧음: {visible_length}자")

    headings, fences_balanced = _heading_entries(article_content)
    if not fences_balanced:
        errors.append("닫히지 않은 코드 펜스가 있음")
    unsupported_headings = [
        f"{kind} H{level}"
        for _position, level, _text, kind in headings
        if kind != "atx"
    ]
    if unsupported_headings:
        errors.append(
            "ATX(#)가 아닌 제목 문법 사용: " + ", ".join(unsupported_headings[:3])
        )
    atx_headings = [entry for entry in headings if entry[3] == "atx"]
    h1 = [text for _position, level, text, _kind in headings if level == 1]
    h2 = [text for _position, level, text, _kind in atx_headings if level == 2]
    if h1:
        errors.append(f"본문 H1 금지: {len(h1)}개")
    if len(h2) < 3:
        errors.append(f"H2 소제목 부족: {len(h2)}개")
    previous_level = 1
    for _position, level, text, _kind in atx_headings:
        if level == 1:
            continue
        if previous_level == 1 and level != 2:
            errors.append(f"첫 본문 제목이 H{level}임: {text}")
            break
        if level > previous_level + 1:
            errors.append(f"제목 계층 점프 H{previous_level}→H{level}: {text}")
            break
        previous_level = level

    intro = _intro_text(article_content)
    if len(intro) < 60:
        errors.append(f"직접 답변 도입부가 너무 짧음: {len(intro)}자")

    faq = front_matter.get("faq") or []
    if faq and not isinstance(faq, list):
        errors.append("FAQ 프론트매터가 목록이 아님")
    elif isinstance(faq, list):
        if len(faq) > 5:
            errors.append(f"FAQ가 5개를 초과함: {len(faq)}개")
        full_plain = _visible_text(full_body)
        questions: set[str] = set()
        for index, item in enumerate(faq, 1):
            if not isinstance(item, dict):
                errors.append(f"FAQ {index}가 객체가 아님")
                continue
            question = _SPACE.sub(" ", str(item.get("question") or "")).strip()
            answer = _SPACE.sub(" ", str(item.get("answer") or "")).strip()
            if not question or not answer:
                errors.append(f"FAQ {index} 질문 또는 답변이 비어 있음")
                continue
            normalized_question = _visible_text(question)
            normalized_answer = _visible_text(answer)
            if not normalized_question or not normalized_answer:
                errors.append(f"FAQ {index}의 화면 표시 질문 또는 답변이 비어 있음")
                continue
            if normalized_question in questions:
                errors.append(f"FAQ 질문 중복: {normalized_question}")
            questions.add(normalized_question)
            if normalized_question not in full_plain or normalized_answer not in full_plain:
                errors.append(f"FAQ {index}가 최종 본문과 정확히 일치하지 않음")

    if require_hero:
        hero = front_matter.get("image")
        if not isinstance(hero, dict) or not str(hero.get("path") or "").strip():
            errors.append("대표 이미지 메타데이터 누락")
        else:
            alt = _SPACE.sub(" ", str(hero.get("alt") or "")).strip()
            if not 5 <= len(alt) <= 160:
                errors.append(f"대표 이미지 alt 길이 부적합: {len(alt)}자")
            if alt.casefold() in _GENERIC_HERO_ALT:
                errors.append(f"대표 이미지 alt가 지나치게 일반적임: {alt}")
    return errors


def _validate_guide(
    front_matter: dict,
    article_content: str,
    full_body: str,
    *,
    require_hero: bool,
) -> None:
    errors = _guide_quality_errors(
        front_matter,
        article_content,
        full_body,
        require_hero=require_hero,
    )
    if errors:
        raise ValueError("가이드 품질 검증 실패: " + "; ".join(errors))


def load_prompt() -> str:
    path = os.path.join(ROOT, "automation", "prompt_config.json")
    cfg = json.load(open(path, encoding="utf-8"))
    shared = cfg.get("keyword_guide_bot", {}).get("system_prompt")
    if not shared:
        raise SystemExit("prompt_config.json 에 keyword_guide_bot.system_prompt 가 없습니다.")
    return shared


def pick_topic(topic_id: str | None) -> dict:
    data = json.load(open(QUEUE, encoding="utf-8"))
    topics = data["topics"]
    if topic_id:
        for t in topics:
            if t["id"] == topic_id:
                return t
        raise SystemExit(f"주제를 찾지 못했습니다: {topic_id}")
    for t in topics:
        if t["status"] == "pending":
            return t
    raise SystemExit("대기 중인 주제가 없습니다. build_topic_queue.py 를 다시 돌리세요.")


def _research_tier(value: object) -> str:
    tier = str(value or "").strip().casefold().replace("-", "_")
    if tier in {"official", "primary", "first_party", "firstparty"}:
        return "official"
    if tier in {"trusted", "independent", "secondary"}:
        return "trusted"
    return ""


def _validate_research_payload(payload: object) -> dict:
    """Keep only reachable direct sources and facts tied to those sources.

    Search-grounded model output is still untrusted input.  In particular, a URL in
    JSON can be invented, redirect to a homepage, or point back to a search result.
    This gate runs before writing and raises when fewer than five usable facts remain,
    which makes the workflow's existing retry loop perform a fresh research pass.
    """
    if not isinstance(payload, dict):
        raise ValueError("가이드 근거 검증 실패: 조사 결과가 객체가 아님")

    raw_facts = payload.get("facts") or []
    if not isinstance(raw_facts, list):
        raise ValueError("가이드 근거 검증 실패: facts가 목록이 아님")
    ordered = sorted(
        (fact for fact in raw_facts if isinstance(fact, dict)),
        key=lambda fact: 0 if _research_tier(fact.get("source_tier")) == "official" else 1,
    )
    probe_cache: dict[str, dict] = {}
    facts: list[dict] = []
    seen_text: set[str] = set()
    seen_fact_source: set[tuple[str, str]] = set()

    for fact in ordered:
        text = _SPACE.sub(" ", str(fact.get("text") or "")).strip()
        source_name = _SPACE.sub(
            " ", str(fact.get("source_name") or "")
        ).strip()
        tier = _research_tier(fact.get("source_tier"))
        source_url = base.canonical_url(fact.get("source_url"))
        text_key = text.casefold()
        if (
            not text
            or not source_name
            or not tier
            or text_key in seen_text
            or base.direct_source_rejection_reason(source_url)
        ):
            continue

        if source_url not in probe_cache:
            result = base.probe_source(source_url)
            probe_cache[source_url] = result if isinstance(result, dict) else {}
        probe = probe_cache[source_url]
        final_url = base.canonical_url(probe.get("url") or source_url)
        if (
            not probe.get("reachable")
            or base.direct_source_rejection_reason(final_url)
        ):
            continue
        identity = (text_key, final_url)
        if identity in seen_fact_source:
            continue

        seen_text.add(text_key)
        seen_fact_source.add(identity)
        facts.append({
            "text": text,
            "source_url": final_url,
            "source_name": source_name,
            "source_tier": tier,
        })

    errors: list[str] = []
    if len(facts) < 5:
        errors.append(f"도달 가능한 직접 근거 사실 5개 미만: {len(facts)}개")
    if not any(fact["source_tier"] == "official" for fact in facts):
        errors.append("공식 또는 1차 근거 없음")
    if errors:
        raise ValueError("가이드 근거 검증 실패: " + "; ".join(errors))

    return {
        "facts": facts,
        "unknowns": [
            _SPACE.sub(" ", str(value)).strip()
            for value in (payload.get("unknowns") or [])
            if _SPACE.sub(" ", str(value)).strip()
        ],
        "volatile": bool(payload.get("volatile")),
    }


def research(client, topic: dict, today: str) -> dict:
    kws = ", ".join(topic["keywords"][:10])
    prompt = f"""오늘은 {today}입니다. 아래 주제로 한국어 실용 가이드를 쓰려고 합니다.
글을 쓰기 전에 웹 검색으로 사실을 모아 주세요.

주제: {topic['primary']}
독자가 실제로 검색하는 표현: {kws}
글의 성격: {topic['format']}

요구사항
- 반드시 웹 검색을 해서 확인된 사실만 담으세요. 기억으로 쓰지 마세요.
- 가격, 요금, 사양, 버전, 한도 같은 수치는 공식 페이지에서 확인하고 원문 표기 그대로 적으세요.
- 각 사실에는 실제로 열리는 출처 URL을 답니다. 검색 결과 페이지나 홈 URL은 안 됩니다.
- source_tier는 공식 문서, 공식 가격표, 제품 공지, 논문 같은 1차 근거면 official,
  독립 전문 매체의 원문 보도면 trusted로 씁니다. 공식 또는 1차 근거를 반드시 포함하세요.
- 확인하지 못한 것은 facts 에 넣지 말고 unknowns 에 적으세요.
- 가격처럼 자주 바뀌는 정보가 포함되면 volatile 을 true 로 하세요.
- 사실은 8개에서 16개 사이로 모으세요."""
    raw = base.generate_content_with_fallback(
        client, prompt,
        response_schema=RESEARCH_SCHEMA,
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    if not raw:
        raise ValueError("가이드 근거 조사 결과가 비어 있음")
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"가이드 근거 JSON 파싱 실패: {exc}") from exc
    return _validate_research_payload(payload)


def write_post(client, topic: dict, evidence: dict, today: str) -> dict:
    facts = "\n".join(
        f"- {f['text']}  (출처: {f['source_name']} {f['source_url']})"
        for f in evidence["facts"]
    )
    unknowns = "\n".join(f"- {u}" for u in evidence.get("unknowns") or []) or "- 없음"
    kws = ", ".join(topic["keywords"][:12])
    prompt = f"""{load_prompt()}

[오늘 날짜]
{today}

[이번 글의 주제]
대표 키워드: {topic['primary']}
글의 성격: {topic['format']}

[반드시 본문 안에서 다뤄야 할 검색 표현]
{kws}
위 표현들은 사람들이 실제로 검색창에 치는 말입니다. 각각을 소제목이나 문장에
자연스럽게 녹여, 이 글 한 편이 이 표현 전부에 답이 되게 하세요.
억지로 나열하지 말고 필요한 것만 자연스럽게 쓰세요.

[확인된 사실. 이것만 쓰세요]
{facts}

[확인하지 못한 것. 모른다고 밝히거나 아예 언급하지 마세요]
{unknowns}

[출력]
content 는 마크다운 본문입니다. 제목(H1)은 넣지 마세요. 검색 질문에 대한 직접 답변
2~4문장을 먼저 쓴 뒤 '## ' 소제목을 시작하세요. 실제 설명문은 4200자에서 6200자
사이로 쓰고 Mermaid, Chart.js 코드와 표 문법은 이 분량에 포함하지 마세요."""
    raw = base.generate_content_with_fallback(client, prompt, response_schema=POST_SCHEMA)
    if not raw:
        raise ValueError("가이드 글 생성 결과가 비어 있음")
    try:
        post = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"가이드 글 JSON 파싱 실패: {exc}") from exc
    _validate_generated_post(post)
    return post


def source_block(evidence: dict, today: str) -> str:
    seen, items = set(), []
    for f in evidence["facts"]:
        url = f["source_url"]
        if url in seen:
            continue
        seen.add(url)
        items.append(f"- [{f['source_name']}]({url}) ({today} 확인)")
    return "\n".join(items)


def save(topic: dict, post: dict, evidence: dict, now) -> str:
    _validate_generated_post(post)
    today = now.strftime("%Y-%m-%d")
    slug = base._safe_slug(post["title_english"])
    filename = f"{today}-{slug}.md"
    os.makedirs(POSTS_DIR, exist_ok=True)
    posts_root = os.path.realpath(POSTS_DIR)
    path = os.path.realpath(os.path.join(posts_root, filename))
    if os.path.commonpath([posts_root, path]) != posts_root:
        raise RuntimeError("잘못된 가이드 게시물 경로")
    if os.path.exists(path):
        raise RuntimeError(f"같은 파일이 이미 있습니다: {filename}")

    article_content = base.strip_emojis(post["content"]).strip()
    article_content = re.sub(r"^#\s+.*\n+", "", article_content)  # 혹시 들어온 H1 제거
    content = insert_glossary_box(article_content)  # 처음 보는 독자용 용어 풀이

    faq = [
        {"question": base.strip_emojis(str(i.get("question", ""))).strip(),
         "answer": base.strip_emojis(str(i.get("answer", ""))).strip()}
        for i in post.get("faq") or []
        if i.get("question") and i.get("answer")
    ]

    title = base.strip_emojis(post["title_korean"]).strip()
    tags = tags_for(title, content, "Tech")

    fm = {
        "layout": "post",
        "automation": AUTOMATION_TAG,
        "title": title,
        "date": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "last_modified_at": now.strftime("%Y-%m-%d %H:%M:%S %z"),
        "categories": "Tech",
        "tags": tags,
        "description": base.strip_emojis(post["description"]).strip(),
        "summary": base.strip_emojis(post["summary"]).strip(),
        "topic_id": topic["id"],
        "target_keyword": topic["primary"],
        "keyword_tier": topic["tier"],
        "sitemap": True,
    }
    if faq:
        fm["faq"] = faq
    # Chirpy는 프론트매터로 옵트인해야 mermaid와 Chart.js 스크립트를 로드한다.
    # 이게 빠지면 코드블록이 날것으로 노출된다.
    if base._fenced_blocks(content, "mermaid"):
        fm["mermaid"] = True
    if base._fenced_blocks(content, "chartjs"):
        fm["chart"] = True

    body = [content, ""]
    if faq:
        body += ["## 자주 묻는 질문", ""]
        for i in faq:
            body += [f"### {i['question']}", "", i["answer"], ""]
    body += ["## 직접 확인한 원문", "", source_block(evidence, today)]
    if evidence.get("volatile"):
        body += ["", "위 수치는 확인 시점 기준이며 예고 없이 바뀔 수 있습니다. "
                     "결정 전에 공식 페이지를 한 번 더 확인하시기 바랍니다."]

    full_body = "\n".join(body).rstrip() + "\n"
    # 본문 품질 실패라면 카드 파일조차 만들지 않는다. 이 예외는 main까지 전파되어
    # Actions의 기존 3회 재시도 루프가 다음 생성 시도를 수행한다.
    _validate_guide(fm, article_content, full_body, require_hero=False)
    try:
        image_path = generate_card(slug, title, "Tech", tags, today)
    except Exception as exc:
        raise RuntimeError(f"대표 이미지 생성 실패: {exc}") from exc
    fm["image"] = {
        "path": image_path,
        "alt": f"{title[:60]} 대표 이미지",
    }
    _validate_guide(fm, article_content, full_body, require_hero=True)

    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{filename}.", suffix=".tmp", dir=posts_root
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.safe_dump(
                fm,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
            f.write("---\n\n")
            f.write(full_body)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return filename


def _load_ledger() -> dict:
    if not os.path.exists(LEDGER):
        return {"written": {}}
    with open(LEDGER, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("written_topics.json 최상위 값이 객체가 아님")
    written = data.setdefault("written", {})
    if not isinstance(written, dict):
        raise ValueError("written_topics.json written 값이 객체가 아님")
    return data


def _filename_from_ledger(topic_id: str) -> str | None:
    value = str(_load_ledger().get("written", {}).get(topic_id) or "").strip()
    if not value:
        return None
    filename = os.path.basename(value)
    return filename if filename.endswith(".md") else f"{filename}.md"


def _guide_front_matter(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read(120_000)
        if not raw.startswith("---"):
            return {}
        return yaml.safe_load(raw.split("---", 2)[1]) or {}
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        return {}


def existing_topic_filename(topic: dict) -> str | None:
    """Find a committed or crash-left publication for one queue topic."""
    ledger_filename = _filename_from_ledger(topic["id"])
    if ledger_filename and os.path.isfile(os.path.join(POSTS_DIR, ledger_filename)):
        return ledger_filename
    if not os.path.isdir(POSTS_DIR):
        return None
    for filename in sorted(os.listdir(POSTS_DIR), reverse=True):
        if not filename.endswith(".md"):
            continue
        metadata = _guide_front_matter(os.path.join(POSTS_DIR, filename))
        if metadata.get("automation") != AUTOMATION_TAG:
            continue
        if str(metadata.get("topic_id") or "") == str(topic["id"]):
            return filename
        # Posts written before topic_id was introduced can still repair their ledger.
        if not metadata.get("topic_id") and str(
            metadata.get("target_keyword") or ""
        ) == str(topic.get("primary") or ""):
            return filename
    return None


def mark_written(topic_id: str, filename: str) -> None:
    data = _load_ledger()
    value = filename[:-3] if filename.endswith(".md") else filename
    if data["written"].get(topic_id) == value:
        return
    data["written"][topic_id] = value
    ledger_dir = os.path.dirname(os.path.realpath(LEDGER))
    os.makedirs(ledger_dir, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".written_topics.", suffix=".tmp", dir=ledger_dir
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, LEDGER)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def publish(topic: dict, post: dict, evidence: dict, now) -> str:
    """Commit a guide and its ledger entry as one retry-safe operation."""
    existing = existing_topic_filename(topic)
    if existing:
        mark_written(topic["id"], existing)
        return existing

    filename = save(topic, post, evidence, now)
    path = os.path.join(POSTS_DIR, filename)
    try:
        mark_written(topic["id"], filename)
    except Exception as exc:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError as rollback_exc:
            raise RuntimeError(
                "가이드 원장 기록 실패 후 게시물 롤백도 실패했습니다: "
                f"{rollback_exc}"
            ) from exc
        raise RuntimeError("가이드 원장 기록 실패로 게시물을 롤백했습니다") from exc
    return filename


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--topic-id")
    args = ap.parse_args()

    now = base.kst_now()
    today = now.strftime("%Y-%m-%d")
    topic = pick_topic(args.topic_id)
    print(f"주제: [{topic['tier']}] {topic['primary']}  ({topic['format']}, 변형 {topic['variants']}개)")

    if not args.dry_run:
        existing = existing_topic_filename(topic)
        if existing:
            mark_written(topic["id"], existing)
            print(f"이미 발행된 주제를 원장과 동기화했습니다: _posts/{existing}")
            return 0

    client = base.get_gemini_client()
    evidence = research(client, topic, today)
    print(f"확인된 사실 {len(evidence['facts'])}개 / 미확인 {len(evidence.get('unknowns') or [])}개")
    if len(evidence["facts"]) < 5:
        print("근거가 너무 적어 발행을 중단합니다.")
        return 1

    post = write_post(client, topic, evidence, today)
    print(f"제목: {post['title_korean']}")
    print(f"본문 {len(post['content'])}자 / FAQ {len(post.get('faq') or [])}개")

    if args.dry_run:
        print("\n[드라이런] 저장하지 않았습니다.\n")
        print(post["content"][:1200])
        return 0

    filename = publish(topic, post, evidence, now)
    print(f"발행 완료: _posts/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
