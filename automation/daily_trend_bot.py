import os
import datetime
import yaml
import requests
from google import genai
from google.genai import types

# Configuration
POSTS_DIR = "../_posts"
FALLBACK_THUMBNAIL = "/assets/img/logo.png"
FALLBACK_MODELS = ["gemini-3.1-pro-preview", "gemini-3-pro-preview", "gemini-3-flash-preview"]

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
            return data
        except Exception as e:
            print(f"Error parsing blog post JSON: {e}")
    return None

def save_post(post_data):
    """Saves the post to a file."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    korea_time = utc_now + datetime.timedelta(hours=9)
    date_str = korea_time.strftime("%Y-%m-%d")
    
    # Use English title for filename
    safe_title = "".join([c if c.isalnum() or c == '-' else "" for c in post_data.get('title_english', 'New-Post').replace(" ", "-")]).strip("-")
    filename = f"{date_str}-{safe_title}.md"
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

    front_matter = {
        "layout": "post",
        "title": post_data.get('title_korean', post_data.get('title', 'Untitled')),
        "date": f"{date_str}",
        "categories": "Tech", # Single category
        "summary": post_data['summary'],
        "author": "AI Trend Bot",
        "github_url": github_url
    }
    
    if image_data:
        front_matter["image"] = image_data
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, allow_unicode=True, sort_keys=False)
        f.write("---\n\n")
        
        content = post_data['content']
        if '\\n' in content:
            content = content.replace('\\n', '\n')
            
        f.write(content)
        
        if post_data.get('reference_links'):
            f.write("\n\n## References\n")
            for link in post_data['reference_links']:
                f.write(f"- {link}\n")
                
    print(f"Saved post to {filepath}")

def main():
    try:
        client = get_gemini_client()
        
        # 1. Find Trends (List)
        topics_list = find_trending_topic(client)
        
        if not topics_list:
            print("No trending topics found.")
            return

        posts_to_generate = 10
        posts_count = 0
        
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
                # break # We only want 1 post per run -> removed break for 10 posts
            else:
                print(f"Failed to generate post content for {topic_name}. Trying next...")
                
        if not post_generated:
            print("All trending topics were either duplicates or failed to generate.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
