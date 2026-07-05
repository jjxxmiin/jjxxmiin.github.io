"""
Daily AI-stocks curation -> _data/ai_stocks.yml (rendered by _tabs/stocks.md, the STOCKS tab).
Uses Gemini + Google Search to pick AI-related stocks (US + Korea) — core leaders plus
rotating/notable current plays — with an AI focus line and blog-correlation keywords.
Runs daily via .github/workflows/daily_stocks.yml.

  GEMINI_API_KEY=... python ai_stocks_bot.py
  AI_STOCKS_OUT=/tmp/x.yml python ai_stocks_bot.py     # write elsewhere (testing)
"""
import os
import re
import json
import datetime
import yaml
from google import genai
from google.genai import types

OUT_PATH = os.environ.get("AI_STOCKS_OUT") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "_data", "ai_stocks.yml"
)
MODELS = ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-flash-latest"]


def kst_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def clean(t):
    t = re.sub(r"\s*\[\d[\d.]*\]", "", str(t or ""))
    return t.replace("·", "/").strip()


def generate(client, today_str):
    prompt = f"""오늘은 {today_str}이다. AI(인공지능)와 관련된 상장 주식을 큐레이션하라.

[규칙]
- 미국(US) 8~10개 + 한국(KR) 4~6개. AI와의 관련성이 분명한 종목만.
- '핵심 리더'(NVIDIA, Microsoft, 삼성전자 등)와 함께, 최근 AI 흐름에서 '그날그날 달라지는 주목주'(AI 반도체 밸류체인, 데이터센터/전력, 신규 상장, 이번 주 화제 종목 등)를 섞어 다양하게 골라라. 매번 똑같은 목록이 되지 않게 하라.
- 각 종목: ticker(예: NVDA, 005930), name(회사명), market("US" 또는 "KR"), exchange("NASDAQ"/"NYSE"/"KRX"), focus(그 회사의 AI 포인트를 담백하게 한 줄), keywords(그 회사의 제품/기술/브랜드명 소문자 영문·한글 3~7개 — 개발자 글에서 언급될 만한 단어).
- 과장/이모지/상투어 금지. 가운뎃점 '·' 금지(필요하면 '/'). 사실 기반으로.
- 확인 안 되는 종목/티커는 넣지 마라."""

    schema = {
        "type": "OBJECT",
        "properties": {
            "stocks": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "ticker": {"type": "STRING"},
                        "name": {"type": "STRING"},
                        "market": {"type": "STRING"},
                        "exchange": {"type": "STRING"},
                        "focus": {"type": "STRING"},
                        "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
                    },
                    "required": ["ticker", "name", "market", "exchange", "focus", "keywords"],
                },
            }
        },
        "required": ["stocks"],
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
    data = generate(client, f"{now.year}.{now.month}.{now.day}")
    if not data or not data.get("stocks"):
        raise SystemExit("stocks generation failed")

    out_stocks = []
    seen = set()
    for s in data["stocks"]:
        tk = clean(s.get("ticker"))
        mk = (s.get("market") or "").strip().upper()
        if not tk or mk not in ("US", "KR") or tk in seen:
            continue
        seen.add(tk)
        exch = (s.get("exchange") or ("KRX" if mk == "KR" else "NASDAQ")).strip().upper()
        kws = [clean(k) for k in (s.get("keywords") or []) if clean(k)]
        out_stocks.append({
            "ticker": tk,
            "name": clean(s.get("name")),
            "market": mk,
            "gf": f"{tk}:{exch}",
            "focus": clean(s.get("focus")),
            "keywords": kws,
        })

    # keep US first then KR (page groups by market anyway)
    out_stocks.sort(key=lambda x: 0 if x["market"] == "US" else 1)
    out = {"updated": now.strftime("%Y-%m-%d"), "stocks": out_stocks}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# AI 관련 주식 — automation/ai_stocks_bot.py 가 매일 갱신 (수동 편집도 가능)\n")
        yaml.dump(out, f, allow_unicode=True, sort_keys=False, width=1000)
    us = sum(1 for s in out_stocks if s["market"] == "US")
    print(f"wrote {OUT_PATH} | {len(out_stocks)} stocks (US {us}, KR {len(out_stocks) - us})")


if __name__ == "__main__":
    main()
