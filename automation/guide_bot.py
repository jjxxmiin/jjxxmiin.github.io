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
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.genai import types  # noqa: E402

import daily_trend_bot as base  # noqa: E402
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
                },
                "required": ["text", "source_url", "source_name"],
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
- 확인하지 못한 것은 facts 에 넣지 말고 unknowns 에 적으세요.
- 가격처럼 자주 바뀌는 정보가 포함되면 volatile 을 true 로 하세요.
- 사실은 8개에서 16개 사이로 모으세요."""
    raw = base.generate_content_with_fallback(
        client, prompt,
        response_schema=RESEARCH_SCHEMA,
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    return json.loads(raw)


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
content 는 마크다운 본문입니다. 제목(H1)은 넣지 마세요. '## '로 시작하는
소제목부터 씁니다. 분량은 3500자에서 5500자 사이입니다."""
    raw = base.generate_content_with_fallback(client, prompt, response_schema=POST_SCHEMA)
    return json.loads(raw)


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
    today = now.strftime("%Y-%m-%d")
    slug = base._safe_slug(post["title_english"])
    filename = f"{today}-{slug}.md"
    path = os.path.join(POSTS_DIR, filename)
    if os.path.exists(path):
        raise RuntimeError(f"같은 파일이 이미 있습니다: {filename}")

    content = base.strip_emojis(post["content"]).strip()
    content = re.sub(r"^#\s+.*\n+", "", content)  # 혹시 들어온 H1 제거

    faq = [
        {"question": base.strip_emojis(str(i.get("question", ""))).strip(),
         "answer": base.strip_emojis(str(i.get("answer", ""))).strip()}
        for i in post.get("faq") or []
        if i.get("question") and i.get("answer")
    ][:5]

    title = base.strip_emojis(post["title_korean"]).strip()
    tags = tags_for(title, content, "Tech")
    try:
        image = {"path": generate_card(slug, title, "Tech", tags, today),
                 "alt": f"{title[:60]} 대표 이미지"}
    except Exception as exc:
        print(f"카드 생성 실패({exc}). 대표 이미지 없이 발행합니다.")
        image = None

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
        "target_keyword": topic["primary"],
        "keyword_tier": topic["tier"],
        "sitemap": True,
    }
    if image:
        fm["image"] = image
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

    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(fm, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        f.write("---\n\n")
        f.write("\n".join(body).rstrip() + "\n")
    return filename


def mark_written(topic_id: str, filename: str) -> None:
    data = {"written": {}}
    if os.path.exists(LEDGER):
        data = json.load(open(LEDGER, encoding="utf-8"))
    data.setdefault("written", {})[topic_id] = filename[:-3]
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--topic-id")
    args = ap.parse_args()

    now = base.kst_now()
    today = now.strftime("%Y-%m-%d")
    topic = pick_topic(args.topic_id)
    print(f"주제: [{topic['tier']}] {topic['primary']}  ({topic['format']}, 변형 {topic['variants']}개)")

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

    filename = save(topic, post, evidence, now)
    mark_written(topic["id"], filename)
    print(f"발행 완료: _posts/{filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
