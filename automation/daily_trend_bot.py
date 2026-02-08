import os
import datetime
import yaml
import requests
from google import genai
from google.genai import types

# Configuration
POSTS_DIR = "../_posts"
FALLBACK_THUMBNAIL = "/assets/img/logo.png"

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    return genai.Client(api_key=api_key)

def find_trending_topic(client):
    """
    Uses Gemini with Google Search to find today's trending AI topics.
    Returns a list of dictionaries with 'topic_name', 'github_url', 'description', 'search_query'.
    """
    print("Searching for trending AI topics from GitHub Trending (Daily)...")
    
    prompt = """
    Target: https://github.com/trending?since=daily
    Task: Find the **Top 5** most "hot" and trending AI open source projects from `github.com/trending?since=daily` (Daily Trending).
    
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
    
    tools = [types.Tool(google_search=types.GoogleSearch())]
    
    # Use gemini-3-pro-preview with thinking
    response = client.models.generate_content(
        model="gemini-3-pro-preview", 
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=tools,
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
        )
    )
    
    if response.text:
        import json
        import re
        try:
            text = response.text.strip()
            # Try to find JSON list
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                text = match.group(0)
            elif text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            # Ensure it's a list
            if isinstance(data, dict):
                data = [data]
                
            print(f"Identified {len(data)} potential trends.")
            for item in data:
                print(f"- {item.get('topic_name')}: {item.get('description')}")
                
            return data
        except Exception as e:
            print(f"Error parsing trend data: {e}")
            print(f"Raw text: {response.text}")
            return []
    return []

def check_duplication(topic_name):
    """Checks if a post about this topic already exists."""
    if not os.path.exists(POSTS_DIR):
        return False
        
    topic_clean = topic_name.lower().replace(" ", "")
    
    for filename in os.listdir(POSTS_DIR):
        if filename.endswith(".md"):
            # Simple check: is the topic name part of the filename?
            # Filenames are usually YYYY-MM-DD-title.md
            if topic_clean in filename.lower().replace("-", ""):
                print(f"Skipping: Post likely exists for {topic_name} ({filename})")
                return True
    return False

def generate_blog_post(client, topic_data):
    """Generates a detailed blog post about the topic."""
    
    topic_name = topic_data['topic_name']
    github_url = topic_data.get('github_url', '')
    search_query = topic_data.get('search_query', topic_name + " AI github features technology details")
    
    print(f"Generating content for: {topic_name} (URL: {github_url}) using query: {search_query}")
    
    prompt_text = f"""
    **Role:** Expert Tech Columnist (Professional but Accessible)
    **Task:** Write a high-quality, professional, yet easy-to-read blog post in **Korean** about: **{topic_name}**.
    
    **Research & Verification (CRITICAL):**
    1.  **Target Repository**: **{github_url}**
    2.  **Verify Content**: You MUST access and read the README/Documentation of this specific URL.
    3.  **Scope**: Cover **EVERYTHING** in the README. If the README is long, summarize all sections (Features, Installation, Usage, Configuration, Architecture, Contributing, etc.). Do not miss major details.
    
    **Content Structure:**
    1.  **Title (Korean)**: Catchy, Viral, and "Click-worthy" (e.g., "Developer jobs in danger? This AI Agent is crazy...").
    2.  **Title (English)**: Simple, descriptive title for the filename (e.g., "OpenClaw-The-AI-Agent").
    3.  **Introduction**: Hook the reader. Explain the unique value.
    4.  **Key Features**: Comprehensive breakdown of ALL features mentioned in README.
    5.  **Deep Dive / Architecture**: Explain how it works internally.
    6.  **Installation & Setup**: Detailed step-by-step from README.
    7.  **Usage Guide**: How to use it after installation.
    8.  **Use Cases**: Real-world scenarios.
    9.  **Comparison**: Pros and cons.
    10. **Conclusion**: Final verdict.
    
    **Constraints:**
    - **Language**: Korean (Body & Main Title). Polite, professional tone (~합니다/해요).
    - **Formatting**: Markdown. Bold emphasis.
    - **Content**: **DO NOT INCLUDE 'Author' or 'Date' lines in the body text.**
    - **Images**: **DO NOT** embed images in the body text. Text only.
    - **Length**: Extremely detailed. 3000+ characters.
    
    **Output Schema (JSON):**
    Return a JSON object with:
    - title_korean: String (Korean, Catchy)
    - title_english: String (English, for filename, dashes used for spaces)
    - summary: String (for front matter, **KOREAN**)
    - content: String (Markdown body, Text ONLY, NO images)
    - reference_links: List[String] (URLs found)

    IMPORTANT: Return ONLY the JSON object, starting with {{ and ending with }}.
    """
    
    tools = [types.Tool(google_search=types.GoogleSearch())]
    
    response = client.models.generate_content(
        model="gemini-3-pro-preview", 
        contents=prompt_text,
        config=types.GenerateContentConfig(
            tools=tools,
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
        )
    )
    
    if response.text:
        import json
        import re
        try:
            text = response.text.strip()
            # Try to find JSON object
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                text = match.group(0)
            elif text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            data = json.loads(text.strip())
            # Inject github_url so save_post can use it
            data['github_url'] = github_url
            return data
        except Exception as e:
            print(f"Error parsing blog post JSON: {e}")
            print(f"Raw text: {response.text[:500]}...")
            return None
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
        "date": f"{date_str} 16:00:00 +0900",
        "categories": "Tech", # Single category
        "summary": post_data['summary'],
        "author": "AI Trend Bot"
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

        post_generated = False
        
        for topic_data in topics_list:
            topic_name = topic_data['topic_name']
            
            # 2. Check Duplication
            if check_duplication(topic_name):
                continue # Try next topic
            
            print(f"Selected topic: {topic_name}")
            
            # 3. Generate Post
            post_data = generate_blog_post(client, topic_data)
            
            if post_data:
                # 4. Save
                save_post(post_data)
                post_generated = True
                break # We only want 1 post per run
            else:
                print(f"Failed to generate post content for {topic_name}. Trying next...")
                
        if not post_generated:
            print("All trending topics were either duplicates or failed to generate.")
            
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
