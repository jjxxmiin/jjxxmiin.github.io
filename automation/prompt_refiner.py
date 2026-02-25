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

class PromptRefiner:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found")
        self.client = genai.Client(api_key=self.api_key)
        self.ga_client = GA4Client()

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
        # Filter for minimum views to avoid noise in Bottom selection
        reliable_posts = [p for p in valid_posts if p['views'] >= 5]
        if not reliable_posts:
            # Fallback to valid_posts if no post has >= 5 views
            reliable_posts = valid_posts

        sorted_posts = sorted(reliable_posts, key=lambda x: x['avg_engagement_time'], reverse=True)
        
        top_3 = sorted_posts[:3]
        bottom_3 = sorted_posts[-3:] if len(sorted_posts) > 3 else []
        
        # Avoid overlap if total reliable posts < 6
        if len(sorted_posts) > 3 and len(sorted_posts) < 6:
            bottom_3 = [p for p in bottom_3 if p not in top_3]

        context_data = {
            "top_performing_posts": top_3,
            "low_performing_posts": bottom_3
        }

        print(f"Analyzing {len(top_3)} top and {len(bottom_3)} bottom posts with Gemini (3.1 Pro + Thinking)...")
        
        # Load current config
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            current_config = json.load(f)

        meta_prompt = f"""
        너는 최고 수준의 블로그 콘텐츠 분석가이자 프롬프트 엔지니어링 전문가야.
        내 블로그의 성과 데이터를 기반으로 시스템 프롬프트를 개선하는 것이 목표야.

        **분석 데이터 (지난주):**
        1. **성과가 좋은 글들 (Top Engagement):**
        {json.dumps(context_data['top_performing_posts'], ensure_ascii=False, indent=2)}

        2. **성과가 저조한 글들 (Low Engagement - 분석 필요):**
        {json.dumps(context_data['low_performing_posts'], ensure_ascii=False, indent=2)}

        **현재 사용 중인 시스템 프롬프트 (daily_paper_bot):**
        {current_config['daily_paper_bot']['system_prompt']}

        **작업 지시:**
        1. **대조 분석**: 성과가 좋은 글들과 저조한 글들의 차이점을 분석해. (구조, 어조, 도입부의 흥미 유발 요소, 가독성 등)
        2. **문제점 식별**: 저조한 글들이 왜 독자들을 오래 붙잡아두지 못했는지 구체적인 이유를 찾아내.
        3. **전략 수립**: 좋은 글들의 장점을 흡수하고 저조한 글들의 단점을 보완할 수 있는 새로운 가독성 및 가치 전달 전략을 세워.
        4. **프롬프트 개선**: 분석 결과를 바탕으로 `daily_paper_bot`의 시스템 프롬프트를 업데이트해. 
           - **중요**: 기존의 '논문 요약' 역할과 형식을 반드시 유지해야 함.
           - 독자가 첫 문단에서 가치를 느끼게 할 것.
           - 전문 기술 내용을 더 소화하기 쉽게 구조화 할 것.
           - 체류 시간을 늘릴 수 있는 요소(흥미로운 질문, 요약, 비유 등)를 포함할 것.
        5. 출력은 반드시 아래 JSON 스키마를 준수해서 반환해.

        **반드시 포함할 JSON 키:**
        - "analysis": "성과 상위/하위 글들에 대한 대조 분석 내용 (한국어)"
        - "new_system_prompt": "개선된 전체 시스템 프롬프트"

        주의: JSON 형식으로만 응답해.
        """

        tools = [types.Tool(google_search=types.GoogleSearch())]
        
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
            tools=tools,
            response_mime_type="application/json"
        )

        response = self.client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=meta_prompt,
            config=generate_content_config
        )

        if response.text:
            try:
                result = json.loads(response.text)
                new_prompt = result.get("new_system_prompt")
                
                # Check for general purpose keywords if "논문" is missing (maybe AI used synonyms like "기술 블로그" etc.)
                is_valid = False
                if new_prompt:
                    required_keywords = ["논문", "요약", "기술", "블로그", "분석"]
                    keyword_matches = sum(1 for kw in required_keywords if kw.lower() in new_prompt.lower())
                    if keyword_matches >= 2: # At least 2 relevant terms found
                        is_valid = True

                if is_valid:
                    print("New prompt validated. Updating config...")
                    
                    # Backup old config
                    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
                        json.dump(current_config, f, ensure_ascii=False, indent=2)
                    
                    # Update new config
                    current_config['daily_paper_bot']['system_prompt'] = new_prompt
                    current_config['last_updated'] = datetime.date.today().isoformat()
                    current_config['analysis_summary'] = result.get("analysis")
                    
                    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                        json.dump(current_config, f, ensure_ascii=False, indent=2)
                    
                    print("Successfully updated prompt_config.json")
                else:
                    print("Gemini response failed safety validation (not enough relevant keywords).")
                    print(f"Response snippet: {new_prompt[:200] if new_prompt else 'None'}")
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                print(f"Raw Response: {response.text}")

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

