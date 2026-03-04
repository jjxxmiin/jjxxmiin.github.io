import os
import json
import datetime
from google import genai
from google.genai import types
from analytics_client import GA4Client

# Configuration
POSTS_DIR = os.path.join(os.path.dirname(__file__), "../_posts")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "prompt_config.json")
BACKUP_PATH = os.path.join(os.path.dirname(__file__), "prompt_config.backup.json")
FALLBACK_MODELS = ["gemini-3.1-pro-preview", "gemini-3-pro-preview", "gemini-3-flash-preview"]

def get_thinking_config(thinking_level="HIGH"):
    """
    Helper to create ThinkingConfig with fallback for compatibility.
    """
    try:
        if thinking_level == "HIGH":
            return types.ThinkingConfig(thinking_level="HIGH")
        return types.ThinkingConfig(thinking_level=thinking_level)
    except Exception as e:
        print(f"Warning: ThinkingConfig validation failed ({e}). Fallback to include_thoughts=True.")
        return types.ThinkingConfig(include_thoughts=True)

class PromptRefiner:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        self.client = genai.Client(api_key=self.api_key)
        self.ga_client = GA4Client()

    def generate_content_with_fallback(self, contents, response_schema=None, tools=None, thinking_level=None):
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

                response = self.client.models.generate_content(
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

    def get_post_content(self, path):
        """Matches a URL path to a local markdown file and returns its content."""
        # path is like /posts/some-paper/ or /tech/some-paper
        slug = path.strip("/").split("/")[-1].lower()
        if not slug:
            return None
            
        def normalize(s):
            return s.lower().replace("--", "-").replace("_", "-")

        norm_slug = normalize(slug)
            
        # 1. Try exact match (normalized)
        try:
            for filename in os.listdir(POSTS_DIR):
                full_path = os.path.join(POSTS_DIR, filename)
                name_without_ext = os.path.splitext(filename)[0]
                
                # Try simple slug match or Jekyll date-prefix match
                if normalize(name_without_ext) == norm_slug or normalize(name_without_ext).endswith(f"-{norm_slug}"):
                    with open(full_path, "r", encoding="utf-8") as f:
                        return f.read()
        except OSError:
            pass
            
        return None

    def refine_prompts(self):
        print("Fetching engagement data from GA4...")
        metrics = self.ga_client.get_weekly_metrics()
        
        if not metrics:
            print("No metrics found. Skipping refinement.")
            return

        # Prepare context for Gemini
        valid_posts = []
        for m in metrics:
            content = self.get_post_content(m['path'])
            if content:
                valid_posts.append({
                    "url": m['path'],
                    "views": m['views'],
                    "avg_engagement_time": m['avg_engagement_time'],
                    "content_snippet": content[:2000] # Limit context size
                })

        if not valid_posts:
            print("No matching local posts found for the metrics. Skipping.")
            return

        # Contrastive Selection: Top 3 and Bottom 3 by avg_engagement_time
        reliable_posts = [p for p in valid_posts if p['views'] >= 5]
        if not reliable_posts:
            reliable_posts = valid_posts

        sorted_posts = sorted(reliable_posts, key=lambda x: x['avg_engagement_time'], reverse=True)
        top_3 = sorted_posts[:3]
        bottom_3 = sorted_posts[-3:] if len(sorted_posts) > 3 else []
        if len(sorted_posts) > 3 and len(sorted_posts) < 6:
            bottom_3 = [p for p in bottom_3 if p not in top_3]

        context_data = {
            "top_performing_posts": top_3,
            "low_performing_posts": bottom_3
        }

        # Load current config
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            current_config = json.load(f)

        # Refine prompts for each bot
        bots_to_refine = ["daily_paper_bot", "daily_trend_bot"]
        all_analyses = []

        for bot_id in bots_to_refine:
            if bot_id not in current_config:
                continue

            print(f"Analyzing metrics for {bot_id} with Gemini (3.1 Pro + Thinking)...")
            
            meta_prompt = f"""
            너는 최고 수준의 블로그 콘텐츠 분석가이자 프롬프트 엔지니어링 전문가야.
            내 블로그의 성과 데이터를 기반으로 `{bot_id}`의 시스템 프롬프트를 개선하는 것이 목표야.

            **분석 데이터 (지난주):**
            1. **성과가 좋은 글들 (Top Engagement):**
            {json.dumps(context_data['top_performing_posts'], ensure_ascii=False, indent=2)}

            2. **성과가 저조한 글들 (Low Engagement - 분석 필요):**
            {json.dumps(context_data['low_performing_posts'], ensure_ascii=False, indent=2)}

            **현재 사용 중인 시스템 프롬프트 ({bot_id}):**
            {current_config[bot_id]['system_prompt']}

            **작업 지시:**
            1. **대조 분석**: 성과가 좋은 글들과 저조할 글들의 차이점을 분석해. (구조, 어조, 가독성, 그리고 가장 중요한 '사람다움(Human Smell)' 정도 및 콘텐츠의 '깊이(Depth)')
            2. **문제점 식별**: 저조한 글들이 왜 '기계적'이거나 '지루하게' 느껴졌는지, 체류 시간이 짧은 이유를 분석해. (특히 내용이 너무 짧거나 표면적인 정보만 다루지 않았는지 확인)
            3. **프롬프트 개선**: `{bot_id}`의 시스템 프롬프트를 업데이트해.
               - **콘텐츠 강화**: 단순히 요약하지 말고, 기술의 핵심 원리(Architecture), 실제 활용 사례(Use Case), 그리고 개발자로서의 날카로운 분석을 포함하도록 지시를 강화해.
               - **분량 확보**: 독자가 충분한 정보를 얻을 수 있도록 **충분한 분량(2500~3500자 이상)**을 작성하도록 명시해. 
               - **사람 냄새**: 완벽한 정리보다 자연스러운 흐름 중시. 개인적인 의견, 고민하는 흔적, 솔직한 장단점 평가가 드러나도록 해.
               - **가독성 & 리듬**: 문단 길이의 변화를 주어 리듬감을 만들 것.
            4. 출력은 반드시 아래 JSON 스키마를 준수해서 반환해.

            **반드시 포함할 JSON 키:**
            - "analysis": "{bot_id}에 대한 성과 분석 및 개선 방향 (한국어)"
            - "new_system_prompt": "개선된 전체 시스템 프롬프트"

            주의: JSON 형식으로만 응답해.
            """

            tools = [types.Tool(google_search=types.GoogleSearch())]
            
            try:
                response_text = self.generate_content_with_fallback(
                    contents=meta_prompt,
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "analysis": {"type": "STRING"},
                            "new_system_prompt": {"type": "STRING"}
                        },
                        "required": ["analysis", "new_system_prompt"]
                    },
                    tools=tools,
                    thinking_level="HIGH"
                )

                if response_text:
                    result = json.loads(response_text)
                    new_prompt = result.get("new_system_prompt")
                    
                    # Validation: must contain some relevant keywords and mention humans/opinions
                    required_keywords = ["개인", "생각", "인 것 같다"] if bot_id == "daily_trend_bot" else ["논문", "분석"]
                    keyword_matches = sum(1 for kw in required_keywords if kw.lower() in new_prompt.lower())
                    
                    if keyword_matches >= 1:
                        print(f"Successfully refined prompt for {bot_id}.")
                        current_config[bot_id]['system_prompt'] = new_prompt
                        all_analyses.append(f"[{bot_id}] {result.get('analysis')}")
                    else:
                        print(f"Refined prompt for {bot_id} failed safety validation.")
            except Exception as e:
                print(f"Error refining {bot_id}: {e}")

        # Update and Save
        if all_analyses:
            # Backup old config
            with open(BACKUP_PATH, "w", encoding="utf-8") as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)
            
            current_config['last_updated'] = datetime.date.today().isoformat()
            current_config['analysis_summary'] = "\n\n".join(all_analyses)
            
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)
            print("Successfully updated prompt_config.json with refined prompts for both bots.")

    def check_rollback(self):
        """Basic rollback logic: if current traffic is 30% lower than backup's context (simplified)."""
        # In a real scenario, we'd compare the stats before and after prompt update.
        # For now, this is a placeholder for the logic mentioned in the requirements.
        if os.path.exists(BACKUP_PATH):
            print("Checking if rollback is needed... (Placeholder logic)")
            # If traffic drop > 30% detected via external monitor or state file:
            # shutil.copy(BACKUP_PATH, CONFIG_PATH)
            pass

if __name__ == "__main__":
    refiner = PromptRefiner()
    refiner.refine_prompts()
    refiner.check_rollback()

