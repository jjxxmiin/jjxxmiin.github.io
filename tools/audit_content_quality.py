#!/usr/bin/env python3
"""Audit post-level reader, search and answer-engine quality guardrails."""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

import yaml


FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
MATH = re.compile(r"\$\$.*?\$\$|\$[^$\n]+\$", re.DOTALL)
CODE_TAG = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
INLINE_CODE = re.compile(r"`[^`\n]+`")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG = re.compile(r"</?[A-Za-z][^>\n]*>")
LIQUID = re.compile(r"\{[%{].*?[}%]\}")
MARKDOWN_IMAGE = re.compile(r"!\[[^]]*\]\([^)]+\)")
MARKDOWN_IMAGE_DETAILS = re.compile(r"!\[([^]]*)\]\(([^)]+)\)")
MARKDOWN_LINK = re.compile(r"\[([^]]*)\]\([^)]+\)")
EXTERNAL_MARKDOWN_LINK = re.compile(
    r"(?<!!)\[[^]\n]+\]\(\s*(https?://[^)\s]+)", re.IGNORECASE
)
EXTERNAL_HTML_LINK = re.compile(
    r"<a\s+[^>]*href\s*=\s*['\"](https?://[^'\"]+)", re.IGNORECASE
)
POST_URL = re.compile(r"\{%\s*post_url\s+([^\s%]+)\s*%\}")
HEADING = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*$")
LONG_PARAGRAPH = re.compile(r"(?:\n\s*){2,}")
INTERNAL_LINK_BLOCK = re.compile(
    r"<!-- internal-links:start -->.*?<!-- internal-links:end -->", re.DOTALL
)
PRIMARY_SOURCE_BLOCK = re.compile(
    r"<!-- primary-sources:start -->.*?<!-- primary-sources:end -->", re.DOTALL
)
SPACE = re.compile(r"\s+")
HYPE = re.compile(
    r"(게임\s*체인저|충격적(?:인|으로)?|미친\s*(?:성능|도구|프로젝트)|"
    r"무조건\s*(?:써|사|도입)|직접\s+(?:써|사용해|테스트해)\s*보니|"
    r"왜\s*(?:이제야|아무도).*알려|개발자\s*직업이\s*위험)",
    re.IGNORECASE,
)
FALSE_EXPERIENCE = re.compile(
    r"(10년\s*차\s*(?:시니어|엔지니어|개발자)|"
    r"시니어\s*엔지니어로서\s*단언|"
    r"제가\s+(?:직접|최근|현업)|"
    r"직접\s+(?:써|사용해|테스트해)\s*보니)",
    re.IGNORECASE,
)
TITLE_HYPE = re.compile(
    r"(게임.?체인저|충격|미친|궁극의|치명적\s*민낯|\b민낯\b|"
    r"(?:기술|도구|직업|패턴|엔지니어링)의\s*종말|끝났다\??|"
    r"집어삼|뒤집어엎|멱살을\s*잡|구원일까|재앙일까|"
    r"10년\s*차|왜.*(?:이제야|뒤늦게|몰랐)|"
    r"honest\s+review|game.?changer|insane|shocking|ultimate|"
    r"\b(?:salvation|disaster)\b|[\U0001F300-\U0001FAFF])",
    re.IGNORECASE,
)
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
KEYCAP = re.compile(r"[0-9]\ufe0f?\u20e3")
MIDDOT = "\u00b7"


def visible_text(body: str) -> str:
    text = FENCE.sub(" ", body)
    text = LIQUID.sub(" ", text)
    text = MARKDOWN_IMAGE.sub(" ", text)
    text = MARKDOWN_LINK.sub(lambda match: match.group(1) or " ", text)
    text = HTML_COMMENT.sub(" ", text)
    text = HTML_TAG.sub(" ", text)
    text = re.sub(r"(?m)^#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*(?:[-*+] |\d+[.)]\s+|>\s*)", "", text)
    text = re.sub(r"[`*_~|:-]", " ", text)
    return SPACE.sub(" ", text).strip()


def body_without_fences(body: str) -> str:
    return FENCE.sub("", body)


def external_source_urls(body: str) -> set[str]:
    """Return reader-visible external citations, excluding code and comments."""
    clean = FENCE.sub(" ", body)
    clean = HTML_COMMENT.sub(" ", clean)
    clean = LIQUID.sub(" ", clean)
    return {
        *EXTERNAL_MARKDOWN_LINK.findall(clean),
        *EXTERNAL_HTML_LINK.findall(clean),
    }


def intro_text(body: str) -> str:
    clean = body_without_fences(body)
    heading = HEADING.search(clean)
    intro = clean[: heading.start()] if heading else clean
    return visible_text(intro)


def normalized_paragraphs(body: str) -> list[str]:
    clean = PRIMARY_SOURCE_BLOCK.sub(
        "", INTERNAL_LINK_BLOCK.sub("", body_without_fences(body))
    )
    paragraphs: list[str] = []
    for part in LONG_PARAGRAPH.split(clean):
        text = visible_text(part)
        if len(text) >= 180:
            paragraphs.append(text.casefold())
    return paragraphs


def audit(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []
    stats: collections.Counter[str] = collections.Counter()
    posts = sorted((root / "_posts").glob("*.md"))
    ids: set[str] = set()
    permalink_sources: dict[str, Path] = {}
    for post in posts:
        raw = post.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(raw)
        if not match:
            continue
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            continue
        if metadata.get("published", True) is not False:
            ids.add(post.stem)
            slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", post.stem).casefold()
            previous = permalink_sources.get(slug)
            if previous:
                errors.append(
                    f"{post.relative_to(root)}: published permalink collides with "
                    f"{previous.relative_to(root)}"
                )
            else:
                permalink_sources[slug] = post
    seen_paragraphs: dict[str, Path] = {}
    seen_titles: dict[str, Path] = {}
    seen_descriptions: dict[str, Path] = {}

    for path in posts:
        rel = path.relative_to(root)
        raw = path.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(raw)
        if not match:
            errors.append(f"{rel}: front matter missing")
            continue
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: invalid YAML ({exc})")
            continue

        body = raw[match.end() :]
        core_body = PRIMARY_SOURCE_BLOCK.sub("", INTERNAL_LINK_BLOCK.sub("", body))
        plain = visible_text(core_body)
        prose_without_code_or_math = visible_text(
            MATH.sub(" ", INLINE_CODE.sub(" ", CODE_TAG.sub(" ", core_body)))
        )
        visible_len = len(re.sub(r"\s", "", plain))
        reader_visible_len = len(re.sub(r"\s", "", visible_text(body)))
        stats["posts"] += 1
        stats["visible_chars"] += visible_len
        stats["reader_visible_chars"] += reader_visible_len
        if visible_len < 3_200:
            errors.append(f"{rel}: visible body too short ({visible_len})")
        elif reader_visible_len < 3_500:
            warnings.append(
                f"{rel}: reader-visible body below preferred depth "
                f"({reader_visible_len})"
            )

        title = SPACE.sub(" ", str(data.get("title") or "")).strip()
        summary = SPACE.sub(" ", str(data.get("summary") or "")).strip()
        description = SPACE.sub(" ", str(data.get("description") or summary)).strip()
        published = data.get("published", True) is not False
        for field_name, value in (
            ("title", title),
            ("summary", summary),
            ("description", description),
        ):
            if MIDDOT in value:
                errors.append(f"{rel}: middle dot remains in {field_name}")
        if MIDDOT in prose_without_code_or_math:
            errors.append(f"{rel}: stylistic middle dot remains in visible prose")
        if not title:
            errors.append(f"{rel}: title missing")
        elif title.startswith("[") or TITLE_HYPE.search(title):
            match = TITLE_HYPE.search(title)
            reason = match.group(0) if match else "bracketed prefix"
            errors.append(f"{rel}: clickbait or false-experience title phrase `{reason}`")
        if not summary:
            errors.append(f"{rel}: summary missing")
        if not 80 <= len(description) <= 160:
            errors.append(f"{rel}: description length {len(description)}")
        if published and title:
            normalized_title = title.casefold()
            previous = seen_titles.get(normalized_title)
            if previous:
                errors.append(f"{rel}: title duplicates {previous.relative_to(root)}")
            else:
                seen_titles[normalized_title] = path
        if published and description:
            normalized_description = description.casefold()
            previous = seen_descriptions.get(normalized_description)
            if previous:
                errors.append(f"{rel}: description duplicates {previous.relative_to(root)}")
            else:
                seen_descriptions[normalized_description] = path
        if str(data.get("author") or "").strip() == "AI Trend Bot":
            errors.append(f"{rel}: bot is presented as article author")
        sources = external_source_urls(body)
        if published and not sources:
            errors.append(f"{rel}: published article has no reader-visible external source")
        elif published:
            stats["published_posts_with_external_sources"] += 1

        hero = data.get("image")
        if not isinstance(hero, dict) or not str(hero.get("path") or "").strip():
            errors.append(f"{rel}: hero image metadata is missing")
        else:
            hero_alt = SPACE.sub(" ", str(hero.get("alt") or "")).strip()
            if MIDDOT in hero_alt:
                errors.append(f"{rel}: middle dot remains in hero image alt")
            if not 5 <= len(hero_alt) <= 160:
                errors.append(f"{rel}: hero image alt length {len(hero_alt)}")
            if hero_alt.casefold() in {"paper thumbnail", "preview image", "thumbnail"}:
                errors.append(f"{rel}: hero image alt is generic (`{hero_alt}`)")

        clean_body = body_without_fences(body)
        headings = HEADING.findall(clean_body)
        h1 = [text for level, text in headings if level == "#"]
        h2 = [text for level, text in headings if level == "##"]
        if h1:
            errors.append(f"{rel}: body contains H1 ({len(h1)})")
        if len(h2) < 3:
            errors.append(f"{rel}: fewer than 3 H2 sections ({len(h2)})")
        previous_level = 1
        for level, text in headings:
            current_level = len(level)
            if current_level == 1:
                continue
            if previous_level == 1 and current_level != 2:
                errors.append(f"{rel}: first body heading is H{current_level} (`{text}`)")
                break
            if current_level > previous_level + 1:
                errors.append(
                    f"{rel}: heading level jumps H{previous_level} to H{current_level} (`{text}`)"
                )
                break
            previous_level = current_level
        if len(intro_text(body)) < 60:
            errors.append(f"{rel}: direct-answer intro too short ({len(intro_text(body))})")

        faq = data.get("faq") or []
        if faq and not isinstance(faq, list):
            errors.append(f"{rel}: FAQ front matter is not a list")
        elif isinstance(faq, list):
            if len(faq) > 5:
                errors.append(f"{rel}: more than 5 FAQ entries ({len(faq)})")
            questions: set[str] = set()
            for index, item in enumerate(faq, 1):
                if not isinstance(item, dict):
                    errors.append(f"{rel}: FAQ {index} is not an object")
                    continue
                question = SPACE.sub(" ", str(item.get("question") or "")).strip()
                answer = SPACE.sub(" ", str(item.get("answer") or "")).strip()
                if not question or not answer:
                    errors.append(f"{rel}: FAQ {index} has an empty question or answer")
                    continue
                if question in questions:
                    errors.append(f"{rel}: duplicated FAQ question `{question}`")
                questions.add(question)
                question_plain = visible_text(question)
                answer_plain = visible_text(answer)
                if question_plain not in plain or answer_plain not in plain:
                    errors.append(f"{rel}: FAQ {index} does not match visible article text")

        if raw.count("<!-- internal-links:start -->") != 1 or raw.count(
            "<!-- internal-links:end -->"
        ) != 1:
            errors.append(f"{rel}: contextual internal-link block missing or duplicated")
        links = POST_URL.findall(body)
        if len(links) < 2:
            errors.append(f"{rel}: fewer than 2 contextual post links")
        for target in links:
            if target not in ids:
                errors.append(f"{rel}: missing post_url target {target}")

        tags = data.get("tags") or []
        if not isinstance(tags, list) or not 2 <= len(tags) <= 6:
            errors.append(f"{rel}: expected 2-6 controlled tags")

        hype_match = HYPE.search(plain)
        if hype_match:
            warnings.append(f"{rel}: hype/false-experience phrase `{hype_match.group(0)}`")
        false_experience = FALSE_EXPERIENCE.search(plain)
        if false_experience:
            errors.append(
                f"{rel}: unsupported first-person experience phrase "
                f"`{false_experience.group(0)}`"
            )
        emoji_count = len(EMOJI.findall(body_without_fences(body)))
        if emoji_count > 5:
            errors.append(f"{rel}: excessive decorative emoji ({emoji_count})")
        if KEYCAP.search(body_without_fences(body)):
            errors.append(f"{rel}: decorative keycap number remains")

        if raw.count("```") % 2:
            errors.append(f"{rel}: unbalanced fenced code block")

        for alt, target in MARKDOWN_IMAGE_DETAILS.findall(body):
            if not alt.strip():
                errors.append(f"{rel}: image has empty alt text ({target})")
            elif len(alt) > 180:
                errors.append(f"{rel}: image alt text is too long ({len(alt)})")

        for paragraph in normalized_paragraphs(body):
            previous = seen_paragraphs.get(paragraph)
            if previous and previous != path:
                warnings.append(
                    f"{rel}: duplicated long paragraph also in {previous.relative_to(root)}"
                )
            else:
                seen_paragraphs[paragraph] = path

    stats["errors"] = len(errors)
    stats["warnings"] = len(warnings)
    stats["published_posts"] = len(ids)
    return errors, warnings, dict(stats)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--warnings-as-errors", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    errors, warnings, stats = audit(args.root)
    report = {"stats": stats} if args.summary_only else {
        "stats": stats,
        "errors": errors,
        "warnings": warnings,
    }
    print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False))
    return 1 if errors or (args.warnings_as_errors and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
