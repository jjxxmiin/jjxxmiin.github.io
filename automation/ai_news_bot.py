"""
Weekly AI news roundup -> _data/ai_news.yml (rendered by _tabs/news.md, the "AI 소식" tab).
Uses Gemini + Google Search to curate & fact-check the last ~2 weeks of AI tool/model updates,
grouped into fixed categories. Run weekly via .github/workflows/weekly_news.yml.

  GEMINI_API_KEY=... python ai_news_bot.py            # writes ../_data/ai_news.yml
  AI_NEWS_OUT=/tmp/x.yml python ai_news_bot.py         # write elsewhere (testing)
"""
import os
import re
import json
import datetime
import yaml
from google import genai
from google.genai import types


def clean(t):
    """Strip Gemini grounding citation markers like [2.1.7], and the '·' middot (banned)."""
    t = re.sub(r"\s*\[\d[\d.]*\]", "", str(t or ""))
    return t.replace("·", "/").strip()

OUT_PATH = os.environ.get("AI_NEWS_OUT") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "_data", "ai_news.yml"
)
MODELS = ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-flash-latest"]
CATEGORIES = ["프론티어 모델", "코딩 툴", "영상/이미지", "디자인", "음성/음악",
              "검색", "문서/생산성", "오픈소스/중국계", "국내"]


def kst_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def generate(client, today_str):
    prompt = f"""오늘은 {today_str}이다. 최근 1~2주간 '실제로 발표된' AI 툴/모델 업데이트 소식을 큐레이션하라.

[규칙]
- 웹 검색으로 사실을 확인한, 실제로 일어난 소식만 담아라. 추측/미확인/2주 초과 소식은 제외.
- date는 '월/일'(예: "7/1"), text는 "제품명 — 무엇이 어떻게 바뀌었는지"를 구체적으로 한 줄.
- 카테고리 name은 반드시 다음 6개 중에서만: {', '.join(CATEGORIES)}. 각 카테고리 2~5개.
- 과장/이모지/상투어('마법', '핵심', '혁명적', '게임체인저' 등) 금지. 사실/수치 위주.
- 가운뎃점 '·' 문자는 절대 쓰지 마라. 나열/구분이 필요하면 '/' 나 쉼표를 써라.
- big_picture: 이번 주 흐름을 파워블로거처럼 후킹 있고 임팩트 있게, 딱 한 문장으로 요약(단, 과장/이모지 없이 사실 기반).
- 한국어로 작성. 확인 안 되면 넣지 마라."""

    schema = {
        "type": "OBJECT",
        "properties": {
            "big_picture": {"type": "STRING"},
            "categories": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {"type": "STRING"},
                        "items": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {"date": {"type": "STRING"}, "text": {"type": "STRING"}},
                                "required": ["date", "text"],
                            },
                        },
                    },
                    "required": ["name", "items"],
                },
            },
        },
        "required": ["big_picture", "categories"],
    }
    tools = [types.Tool(google_search=types.GoogleSearch())]
    for m in MODELS:
        try:
            print(f"Attempting with {m}...")
            r = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    tools=tools,
                    thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
                ),
            )
            if r.text:
                return json.loads(r.text)
        except Exception as e:
            print(f"  {m} failed: {str(e)[:140]}")
            continue
    return None


def main():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY missing")
    client = genai.Client(api_key=key)

    now = kst_now()
    today_str = f"{now.year}.{now.month}.{now.day}"
    data = generate(client, today_str)
    if not data or not data.get("categories"):
        raise SystemExit("news generation failed")

    by_name = {c["name"].strip(): c.get("items", []) for c in data["categories"]}
    categories = []
    for name in CATEGORIES:  # fixed order, drop unknown/empty
        items = [{"date": clean(it["date"]), "text": clean(it["text"])}
                 for it in by_name.get(name, []) if it.get("date") and it.get("text")]
        if items:
            categories.append({"name": name, "items": items})

    out = {
        "updated": now.strftime("%Y-%m-%d"),
        "title_note": f"최근 1~2주 AI 툴 업데이트 ({today_str} 기준)",
        "big_picture": clean(data["big_picture"]),
        "categories": categories,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# 주간 AI 소식 — automation/ai_news_bot.py 가 매주 갱신 (수동 편집도 가능)\n")
        yaml.dump(out, f, allow_unicode=True, sort_keys=False, width=1000)
    print(f"wrote {OUT_PATH} | {len(categories)} categories, {sum(len(c['items']) for c in categories)} items")


if __name__ == "__main__":
    main()
