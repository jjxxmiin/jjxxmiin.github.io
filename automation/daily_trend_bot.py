import os
import re
import json
import subprocess
import tempfile
import datetime
import yaml
import requests
from google import genai
from google.genai import types

MERMAID_VALIDATOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate_mermaid.mjs")


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


def get_repo_images(github_url, limit=3):
    """Pull REAL embeddable images (screenshots/diagrams) from a repo's README so the
    model can use actual visuals instead of inventing URLs. Filters out badges/shields/
    logos (mostly SVG) so we don't embed junk. Returns a list of image URLs (may be empty)."""
    m = re.search(r'github\.com/([^/]+)/([^/#?]+)', github_url or "")
    if not m:
        return []
    owner, repo = m.group(1), m.group(2).replace(".git", "")
    readme = ""
    for branch in ("main", "master"):
        try:
            r = requests.get(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md", timeout=15)
            if r.status_code == 200 and r.text:
                readme = r.text
                break
        except Exception:
            continue
    if not readme:
        return []
    urls = re.findall(r'!\[[^\]]*\]\((https?://[^)\s]+)', readme)
    urls += re.findall(r'<img[^>]+src=["\'](https?://[^"\']+)', readme)
    bad = ("shields.io", "badge", "discord", "twitter", "x.com", "slsa.dev", "deepwiki",
           "codecov", "circleci", "travis", "buymeacoffee", "ko-fi", "star-history",
           "gitcontributor", "contrib.rocks", "hitcount", "visitor")
    out = []
    for u in urls:
        low = u.lower()
        if any(b in low for b in bad):
            continue
        # screenshots/diagrams are raster; SVGs are almost always badges/logos here
        if not re.search(r'\.(png|jpe?g|gif|webp)(\?|$)', low):
            continue
        u = u.replace("/blob/", "/raw/")
        if u not in out:
            out.append(u)
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# Visual validation: never publish a diagram/chart that renders as an error box.
# ---------------------------------------------------------------------------
def _extract_blocks(content, lang):
    """Return list of (whole_fence, inner_code) for ```<lang> fenced blocks."""
    pat = re.compile(r"```" + lang + r"[ \t]*\n(.*?)```", re.S)
    return [(m.group(0), m.group(1)) for m in pat.finditer(content)]


def _validate_mermaid(codes):
    """Validate mermaid strings with the node parser. Returns [(ok, error), ...].
    If node/validator can't run, skip validation (treat as ok) so we never crash."""
    if not codes:
        return []
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump([c.strip() for c in codes], tf)
            path = tf.name
        out = subprocess.run(["node", MERMAID_VALIDATOR, path],
                             cwd=os.path.dirname(MERMAID_VALIDATOR),
                             capture_output=True, text=True, timeout=150)
        os.unlink(path)
        res = json.loads(out.stdout)
        return [(bool(r.get("ok", True)), r.get("error", "")) for r in res]
    except Exception as e:
        print(f"  (mermaid 검증 건너뜀: {e})")
        return [(True, "")] * len(codes)


def _repair_mermaid(client, code, error):
    prompt = f"""아래 Mermaid 다이어그램에 문법 오류가 있다. 같은 의미를 유지하되 오류만 고쳐라.
[오류] {error}
[규칙]
- erDiagram/classDiagram에서 CLASS, FUNCTION, STATE, END, GRAPH, ORDER, NODE 같은 예약어를 엔티티/클래스 이름으로 쓰지 마라. CODE_CLASS 처럼 접두사를 붙이거나 큰따옴표로 감싼다.
- flowchart 노드 라벨은 큰따옴표로 감싸고 라벨 안에 괄호()·대괄호[]·콜론:을 쓰지 마라.
- 오직 고친 Mermaid 코드 본문만 출력하라 (``` 펜스·설명·따옴표 없이).

[원본]
{code.strip()}"""
    fixed = generate_content_with_fallback(client, prompt)
    if not fixed:
        return None
    fixed = re.sub(r"^```[a-zA-Z]*\n?", "", fixed.strip())
    return re.sub(r"\n?```$", "", fixed).strip()


def _validate_chartjs(code):
    """A chartjs block must be a JSON object with type + data."""
    try:
        cfg = json.loads(code)
        return isinstance(cfg, dict) and bool(cfg.get("type")) and bool(cfg.get("data"))
    except Exception:
        return False


def fix_visuals(client, content):
    """Validate every mermaid/chartjs block. Repair once; if still invalid, drop it —
    so a broken visual never reaches the published post as a red 'Syntax error' box."""
    # Mermaid
    m_blocks = _extract_blocks(content, "mermaid")
    if m_blocks:
        for (whole, inner), (ok, err) in zip(m_blocks, _validate_mermaid([b for _, b in m_blocks])):
            if ok:
                continue
            print(f"  ⚠️ mermaid 오류 → 복구 시도: {err[:70]}")
            fixed = _repair_mermaid(client, inner, err)
            if fixed and _validate_mermaid([fixed])[0][0]:
                content = content.replace(whole, "```mermaid\n" + fixed + "\n```", 1)
                print("     ✅ 복구 성공")
            else:
                content = content.replace(whole, "", 1)
                print("     🗑️ 복구 실패 → 다이어그램 제거")
    # Chart.js (JSON config)
    for whole, inner in _extract_blocks(content, "chartjs"):
        if _validate_chartjs(inner):
            continue
        print("  ⚠️ chartjs JSON 오류 → 제거")
        content = content.replace(whole, "", 1)
    return content

# Configuration
# Resolve relative to THIS file (not the caller's CWD) so it works whether run as
# `cd automation && python daily_trend_bot.py` (CI) or `python automation/daily_trend_bot.py`.
POSTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_posts")
FALLBACK_THUMBNAIL = "/assets/img/logo.png"
# Preview models first (best quality), then stable aliases as a safety net so the
# pipeline keeps working even after a preview model is retired.
FALLBACK_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-latest",
]

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
    Uses Gemini with Google Search to find today's trending AI topics.
    Returns a list of dictionaries with 'topic_name', 'github_url', 'description', 'search_query'.
    """
    print("Searching for trending AI topics from GitHub Trending (Daily)...")
    
    prompt = """
    Target: https://github.com/trending?since=daily
    Task: Find the **Top 15** most "hot" and trending AI open source projects from `github.com/trending?since=daily` (Daily Trending).
    
    Criteria:
    - Must be an AI/ML related project.
    - Must be a repository that is currently trending (high star velocity).
    - Favor projects that are NEW or recently viral over established ones (like pytorch/transformers).
    
    Exclude:
    - Non-AI projects.
    - Collections/Lists (awesome-lists) unless they are extremely viral tools.
    
    Return a JSON LIST of objects (Array), where each object contains:
    - topic_name: The name of the project/tool.
    - github_url: The URL of the GitHub repository.
    - description: A brief 1-sentence description.
    - search_query: A specific search query to get detailed info about this topic.

    IMPORTANT: Return ONLY the JSON LIST, starting with [ and ending with ]. Do not add markdown formatting like ```json.
    """
    
    response_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "topic_name": {"type": "STRING"},
                "github_url": {"type": "STRING"},
                "description": {"type": "STRING"},
                "search_query": {"type": "STRING"}
            },
            "required": ["topic_name", "github_url", "description", "search_query"]
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
        import json
        try:
            data = json.loads(response_text)
            print(f"Identified {len(data)} potential trends.")
            for item in data:
                print(f"- {item.get('topic_name')}: {item.get('description')}")
            return data
        except Exception as e:
            print(f"Error parsing trend data: {e}")
    return []

def check_duplication(github_url, topic_name):
    """
    Checks if a post with this GitHub URL or topic name already exists.
    1. Scans file content for the github_url.
    2. Fallback: Scans filenames for the topic name.
    """
    if not os.path.exists(POSTS_DIR):
        return False
        
    # 1. URL-based check (Primary)
    if github_url:
        clean_url = github_url.strip().rstrip('/')
        print(f"Checking for existing posts with URL: {clean_url}")
        
        for filename in os.listdir(POSTS_DIR):
            if filename.endswith(".md"):
                filepath = os.path.join(POSTS_DIR, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        if clean_url in content:
                            print(f"Skipping: Post already exists for URL {clean_url} ({filename})")
                            return True
                except Exception as e:
                    print(f"Error reading {filename}: {e}")

    # 2. Title-based check (Fallback for old posts)
    topic_clean = topic_name.lower().replace(" ", "")
    print(f"Checking for existing posts with topic: {topic_name} (Clean: {topic_clean})")
    
    for filename in os.listdir(POSTS_DIR):
        if filename.endswith(".md"):
            # Filenames are usually YYYY-MM-DD-title.md
            if topic_clean in filename.lower().replace("-", ""):
                print(f"Skipping: Post likely exists for topic {topic_name} ({filename})")
                return True
                
    return False

def generate_blog_post(client, topic_data):
    """Generates a detailed blog post about the topic."""
    
    topic_name = topic_data['topic_name']
    github_url = topic_data.get('github_url', '')
    search_query = topic_data.get('search_query', topic_name + " AI github features technology details")
    
    print(f"Generating content for: {topic_name} (URL: {github_url}) using query: {search_query}")
    
    # Load prompt from config
    config_path = os.path.join(os.path.dirname(__file__), 'prompt_config.json')
    import json
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            prompt_template = config['daily_trend_bot']['system_prompt']
    except Exception as e:
        print(f"Error loading prompt_config.json: {e}. Using fallback prompt.")
        prompt_template = """
        Write a blog post about {topic_name}.
        Repository: {github_url}
        """

    prompt_text = prompt_template.replace(
        "{topic_name}", topic_name
    ).replace(
        "{github_url}", github_url
    )

    # ROBUSTNESS: the old weekly prompt_refiner.py once rewrote prompt_config.json and
    # dropped the {topic_name}/{github_url} placeholders (2026-05-31), so the topic was
    # never injected and posts drifted off-topic. The refiner is now removed, but we keep
    # this safeguard: always prepend an explicit, unmissable topic block so generation is
    # locked to the selected topic regardless of the config's state.
    # Real images from the repo README (screenshots/diagrams), so the model uses actual
    # visuals instead of inventing placeholder URLs.
    repo_images = get_repo_images(github_url)
    if repo_images:
        img_note = ("사용 가능한 '실제' 이미지 URL (내용과 관련 있을 때만 본문에 ![간단한 설명](URL) 형식으로 1~2개 삽입):\n"
                    + "\n".join(f"  - {u}" for u in repo_images))
    else:
        img_note = "이 저장소에는 쓸 만한 실제 이미지가 없다. 이미지는 넣지 말고 Mermaid 다이어그램과 표로 시각화하라."

    visuals_directive = (
        "[시각 자료 매우 적극 활용 — 그림을 넉넉히, 글 전반에 고르게 배치]\n"
        "1. Mermaid 다이어그램(도형): 6~8개를, 내용에 맞게 '다양한 종류'를 섞어 넣는다. 한 종류만 반복하지 마라.\n"
        "   - 파이프라인/구조 → flowchart TD 또는 LR\n"
        "   - 컴포넌트 상호작용/요청 흐름 → sequenceDiagram\n"
        "   - 데이터 모델/스키마 관계 → erDiagram\n"
        "   - 상태 전이/생명주기 → stateDiagram-v2\n"
        "   - 클래스/모듈 구조 → classDiagram, 구성비 → pie\n"
        "   [Mermaid 문법 안전 규칙 — 반드시 지킬 것]\n"
        "   - erDiagram/classDiagram의 엔티티·클래스 이름에 CLASS, FUNCTION, STATE, END, GRAPH, ORDER, NODE, GROUP 같은 예약어를 쓰지 마라. "
        "CODE_CLASS, CODE_FUNC 처럼 접두사를 붙이거나 이름을 바꾼다.\n"
        "   - flowchart 노드 라벨은 큰따옴표로 감싸고(예: A[\"지식 그래프\"]) 라벨 안에 괄호()·대괄호[]·콜론:을 쓰지 마라.\n"
        "   - 각 다이어그램은 단순하고 문법 오류가 없게 만든다.\n"
        "2. Chart.js(그래프): 벤치마크·수치 비교(토큰 절감량, 속도, 언어 지원 수 등)는 ```chartjs 코드블록에 '유효한 JSON' Chart.js 설정으로 1~2개 넣어라. 예시:\n"
        "   ```chartjs\n"
        "   {\"type\":\"bar\",\"data\":{\"labels\":[\"기존 방식\",\"codebase-memory-mcp\"],\"datasets\":[{\"label\":\"토큰 사용량\",\"data\":[412000,3400]}]}}\n"
        "   ```\n"
        "   반드시 순수 JSON(주석·후행쉼표·홑따옴표 금지)만 넣는다.\n"
        "3. 도표(표): 비교·트레이드오프는 마크다운 표로 여러 개 정리한다. 표 앞뒤에는 반드시 빈 줄을 넣는다.\n"
        "4. 실제 이미지: 아래 제공된 URL만 사용한다. placeholder·via.placeholder·example.com 등 가짜/추측 URL은 절대 만들지 마라.\n"
        "5. 링크: 모든 링크는 [보이는 텍스트](URL) 형태의 클릭 가능한 마크다운으로 쓴다. 맨 URL 노출 금지.\n"
        "6. 이모지: 제목·소제목·본문에 이모지를 쓰지 마라.\n"
        f"{img_note}\n\n"
    )

    topic_header = (
        "[작성 대상 — 반드시 아래 주제로만 작성. 다른 기술로 절대 새지 말 것]\n"
        f"- 프로젝트명: {topic_name}\n"
        f"- GitHub 저장소: {github_url}\n"
        f"- 검색 쿼리: {search_query}\n\n"
        + visuals_directive
    )
    prompt_text = topic_header + prompt_text

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "title_korean": {"type": "STRING"},
            "title_english": {"type": "STRING"},
            "summary": {"type": "STRING"},
            "content": {"type": "STRING"},
            "reference_links": {"type": "ARRAY", "items": {"type": "STRING"}}
        },
        "required": ["title_korean", "title_english", "summary", "content"]
    }

    tools = [types.Tool(google_search=types.GoogleSearch())]
    
    # Generation task: Use HIGH thinking for quality
    response_text = generate_content_with_fallback(
        client, 
        prompt_text, 
        response_schema=response_schema, 
        tools=tools, 
        thinking_level="HIGH"
    )
    
    if response_text:
        import json
        try:
            data = json.loads(response_text)
            data['github_url'] = github_url
            data['content'] = fix_visuals(client, data.get('content', ''))  # validate diagrams/charts
            return data
        except Exception as e:
            print(f"Error parsing blog post JSON: {e}")
    return None

def save_post(post_data):
    """Saves the post to a file."""
    # Calculate US Eastern Time (UTC-5)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    est_time = utc_now - datetime.timedelta(hours=5)
    
    date_filename = est_time.strftime("%Y-%m-%d")
    date_frontmatter = est_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Use English title for filename
    safe_title = "".join([c if c.isalnum() or c == '-' else "" for c in post_data.get('title_english', 'New-Post').replace(" ", "-")]).strip("-")
    filename = f"{date_filename}-{safe_title}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    
    # Construct OpenGraph Image URL
    # Format: https://opengraph.githubassets.com/1/{owner}/{repo}
    github_url = post_data.get('github_url', '')
    image_data = None
    
    if "github.com/" in github_url:
        try:
            # Extract owner/repo
            # github.com/owner/repo
            parts = github_url.split("github.com/")[1].split("/")
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1]
                # Clean up query params or hashes if present
                repo = repo.split("?")[0].split("#")[0]
                
                image_url = f"https://opengraph.githubassets.com/1/{owner}/{repo}"
                image_data = {
                    "path": image_url,
                    "alt": f"{post_data.get('title_english', 'Thumbnail')}"
                }
        except Exception as e:
            print(f"Could not parse GitHub URL for image: {e}")

    # Process the body first so front matter can reflect it (e.g. the mermaid flag).
    content = post_data['content']
    if '\\n' in content:
        content = content.replace('\\n', '\n')
    content = strip_fake_images(content)   # drop placeholder/invented image URLs
    content = strip_emojis(content)        # no decorative emojis in the body
    content = linkify_bare_urls(content)   # make bare URLs clickable [url](url)
    content = fix_table_spacing(content)   # ensure tables render (blank line before/after)

    front_matter = {
        "layout": "post",
        "title": strip_emojis(post_data.get('title_korean', post_data.get('title', 'Untitled'))).strip(),
        "date": date_frontmatter,
        "categories": "Tech", # Single category
        "summary": post_data['summary'],
        "author": "AI Trend Bot",
        "github_url": github_url
    }

    if image_data:
        front_matter["image"] = image_data
    # Chirpy renders ```mermaid blocks only when the post opts in via front matter.
    if re.search(r'```\s*mermaid', content):
        front_matter["mermaid"] = True
    # Our Chart.js include is loaded only when the post has a chart.
    if re.search(r'```\s*chartjs', content):
        front_matter["chart"] = True

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, allow_unicode=True, sort_keys=False)
        f.write("---\n\n")
        f.write(content)
        
        if post_data.get('reference_links'):
            f.write("\n\n## References\n")
            for link in post_data['reference_links']:
                link = str(link).strip()
                if link.startswith("http"):
                    f.write(f"- [{link}]({link})\n")   # clickable
                else:
                    f.write(f"- {link}\n")
                
    print(f"Saved post to {filepath}")

def preflight_check(client):
    """
    Fail LOUDLY (non-zero exit) if the API key is invalid/denied.
    Without this, a dead GEMINI_API_KEY makes find_trending_topic() return []
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
    try:
        client = get_gemini_client()

        # 0. Preflight: dead key -> red run + email instead of silent green
        preflight_check(client)

        # 1. Find Trends (List)
        topics_list = find_trending_topic(client)
        
        if not topics_list:
            print("No trending topics found.")
            return

        posts_to_generate = 1
        posts_count = 0
        post_generated = False
        
        for topic_data in topics_list:
            if posts_count >= posts_to_generate:
                break

            topic_name = topic_data['topic_name']
            github_url = topic_data.get('github_url', '')
            
            # 2. Check Duplication
            if check_duplication(github_url, topic_name):
                continue # Try next topic
            
            print(f"Selected topic ({posts_count+1}/{posts_to_generate}): {topic_name}")
            
            # 3. Generate Post
            post_data = generate_blog_post(client, topic_data)
            
            if post_data:
                # 4. Save
                save_post(post_data)
                post_generated = True
                posts_count += 1
                break # We only want 1 post per run
            else:
                print(f"Failed to generate post content for {topic_name}. Trying next...")
                
        if not post_generated:
            print("All trending topics were either duplicates or failed to generate.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
