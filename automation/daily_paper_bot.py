import os
import datetime
import requests
from google import genai
from google.genai import types
import yaml

# Configuration
HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"
POSTS_DIR = "../_posts"

def fetch_daily_papers():
    """Fetches daily papers from Hugging Face API."""
    try:
        response = requests.get(HF_DAILY_PAPERS_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching papers: {e}")
        return []

def filter_cv_papers(papers):
    """Filters for Computer Vision papers."""
    cv_papers = []
    print(f"Filtering {len(papers)} papers for CV...")
    for i, paper_item in enumerate(papers):
        # The API seems to return a list of items where 'paper' key holds the details
        paper_details = paper_item.get('paper', {})
        
        # Debugging: print first paper's details to confirm structure
        if i == 0:
             # print(f"Sample paper keys: {paper_details.keys()}")
             pass
        
        # Check for tags/categories in the nested 'paper' object
        # 'tags' key was missing, but 'ai_keywords' exists
        keywords = paper_details.get('ai_keywords', [])
        
        # Normalize keywords
        normalized_keywords = [k.lower() for k in keywords]
        
        if i == 0:
             # print(f"Sample keywords: {normalized_keywords}")
             pass

        # Extended CV keywords
        cv_keywords = ['computer vision', 'cv', 'vision', 'object detection', 'image generation', 'segmentation', 'video', 'visual']
        
        is_cv = False
        if any(keyword in k for k in normalized_keywords for keyword in cv_keywords):
            is_cv = True
        
        if is_cv:
            # We want to keep the inner 'paper' object which has 'id', 'title', 'summary', etc.
            # The upvotes are also inside this 'paper' object usually, or at the top level?
            # From debug log: 'upvotes' is in paper_details.
            
            # Inject thumbnail from parent if available
            if 'thumbnail' in paper_item:
                paper_details['thumbnail'] = paper_item['thumbnail']
                
            cv_papers.append(paper_details)
            
    print(f"Found {len(cv_papers)} CV papers.")
    return cv_papers

def generate_blog_post(paper):
    """Generates a blog post using Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    client = genai.Client(api_key=api_key)
    model_id = "gemini-3-flash-preview"

    prompt_text = f"""
    You are an expert Computer Vision researcher and technical blog writer.
    Please write a **comprehensive and detailed technical blog post** in Korean about the following paper.
    The content should be **in-depth**, substantial, and sufficient for a serious researcher to understand the core contributions without reading the full paper immediately.
    
    Paper Title: {paper['title']}
    Paper Abstract: {paper['summary']}
    Paper URL: https://huggingface.co/papers/{paper['id']}
    
    Structure your response in Markdown with the following sections. Ensure each section is detailed:

    1. **Title**: Catchy Korean title (translated or adapted).
    2. **One-line Summary**: A single sentence summarizing the key contribution.
    3. **Introduction**:
        - What is the problem being solved?
        - Why is this challenging?
        - What are the limitations of existing approaches?
    4. **Methodology (In-Depth)**:
        - Explain the core architecture and algorithms in detail.
        - Describe key components (e.g., loss functions, modules, training strategies).
        - Use bullet points or numbered lists for clarity but maintain detailed explanations.
    5. **Experiments & Results**:
        - What datasets were used?
        - How does it compare to SOTA (State of the Art) methods?
        - Highlight key quantitative metrics.
    6. **Discussion**:
        - What are the main strengths of this work?
        - What are the limitations or potential weaknesses?
    7. **Conclusion**: Summary and future impact.
    
    **Tone**: Professional, technical, yet accessible to AI engineers.
    **Length**: Aim for a long, rich post (not just a brief summary).
    
    Do NOT include the Front Matter (YAML) in the output, I will add it programmatically.
    Just return the Markdown content.
    """

    tools = [
        types.Tool(google_search=types.GoogleSearch())
    ]
    
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=False, # We don't want thoughts in the final blog post file usually, unless user wants to see them.
            # User snippet had `thinking_level="HIGH"`. This param might not be in the SDK yet or varies.
            # The SDK usually takes `include_thoughts=True/False`.
            # I will omit specific thinking_level if not sure, or check snippets.
            # Actually current SDK `types.ThinkingConfig` might not take `thinking_level`. 
            # I will omit strict config and just leave it default if I use a thinking model.
            # Wait, `gemini-2.0-flash-thinking-exp-1219` automatically thinks.
            # If I use `google-genai` SDK, I should follow its structure.
        ),
        tools=tools,
        temperature=0.7 # standard
    )
    
    # User snippet used:
    # generate_content_config = types.GenerateContentConfig(
    #    thinking_config=types.ThinkingConfig(
    #        thinking_level="HIGH",
    #    ),
    #    tools=tools,
    # )
    # I will try to match that, assuming they know the SDK version they are asking for.
    
    # Construct contents
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
            ],
        ),
    ]

    response_text = ""
    # Use streaming as requested/shown
    for chunk in client.models.generate_content_stream(
        model=model_id,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.text:
            response_text += chunk.text
            
    return response_text

def save_post(paper, content):
    """Saves the blog post to the _posts directory."""
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    
    # Sanitize title for filename
    safe_title = "".join([c if c.isalnum() else "-" for c in paper['title']]).strip("-")
    filename = f"{date_str}-{safe_title}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    
    # Extract summary from content
    summary = "최신 Computer Vision 논문 리뷰" # Default
    try:
        import re
        # Look for: 2. **One-line Summary**: ... or similar
        # Also look for Korean header: ### 한 줄 요약
        # We search for the header, then capture the next non-empty line
        
        # Regex for "### 한 줄 요약" or "### **One-line Summary**" followed by content
        # Robust regex: Find line with "One-line Summary" or "한 줄 요약", then capture the next non-empty line
        summary_match = re.search(r"(?:One-line Summary|한 줄 요약).*?\n+(.+)", content)
        if summary_match:
             # Remove bolding ** if present
             clean_summary = summary_match.group(1).replace("**", "").strip()
             if clean_summary:
                 summary = clean_summary
        else:
             # Fallback to previous pattern
             match = re.search(r"One-line Summary\*\*:\s*(.*)", content)
             if match:
                summary = match.group(1).strip()
    except Exception as e:
        print(f"Warning: Could not extract summary: {e}")

    # Front Matter
    front_matter = {
        "layout": "post",
        "title": f"[{paper.get('publishedAt', date_str)[:10]}] {paper['title']}", # Fallback
        "date": date_str, # YYYY-MM-DD
        "categories": "tech", 
        "math": True,
        "summary": summary
    }
    
    # Extract Korean title from H1 (# Title)
    try:
        # Search for first line starting with #
        h1_match = re.search(r"^#\s+(.*)", content, re.MULTILINE)
        if h1_match:
             korean_title = h1_match.group(1).strip()
             if korean_title:
                 front_matter['title'] = korean_title
        else:
             # Fallback to **Title**: pattern
             title_match = re.search(r"Title\*\*:\s*(.*)", content)
             if title_match:
                 korean_title = title_match.group(1).strip()
                 if korean_title:
                     front_matter['title'] = korean_title
    except:
        pass

    # Add image if available (Preserving this feature)
    if 'thumbnail' in paper:
         # Check if user wants image in this specific format or just standard?
         # User didn't show image in example, but previous request was important.
         # I'll keep it but maybe as a clear 'image' param if Jekyll theme supports it.
         # Chirpy theme (detected in config) supports 'image' with 'path' and 'alt'.
         front_matter['image'] = {
            "path": paper['thumbnail'],
            "alt": "Paper Thumbnail"
        }
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, allow_unicode=True, sort_keys=False) # sort_keys=False to keep order roughly
        f.write("---\n\n")
        f.write(content)
        f.write(f"\n\n[Original Paper Link](https://huggingface.co/papers/{paper['id']})")

    print(f"Saved post to {filepath}")

def get_posted_paper_ids():
    """Scans existing posts to find IDs of papers already posted."""
    posted_ids = set()
    if not os.path.exists(POSTS_DIR):
        print(f"Warning: Posts directory {POSTS_DIR} does not exist.")
        return posted_ids

    print("Checking for existing papers...")
    for filename in os.listdir(POSTS_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(POSTS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Look for the link pattern we add at the bottom
                    # [Original Paper Link](https://huggingface.co/papers/{id})
                    # Or just search for huggingface.co/papers/id
                    import re
                    match = re.search(r"huggingface\.co/papers/(\S+?)\)", content)
                    if match:
                        posted_ids.add(match.group(1))
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    
    print(f"Found {len(posted_ids)} already posted papers.")
    return posted_ids

def main():
    print("Fetching papers...")
    papers = fetch_daily_papers()
    print(f"Fetched {len(papers)} papers.")
    
    cv_papers = filter_cv_papers(papers)
    posted_ids = get_posted_paper_ids()
    
    target_paper = None
    
    # Sort CV papers by upvotes
    if cv_papers:
        # Sort based on inner upvotes
        cv_papers.sort(key=lambda x: x.get('upvotes', 0), reverse=True)
        
        # Iterate and find first one not posted
        for paper_item in cv_papers:
            # We already unwrapped details in filter_cv_papers so 'paper_item' here IS the details dict
            # Wait, let's double check filter_cv_papers logic.
            # In validation step 204: "cv_papers.append(paper_details)"
            # So cv_papers contains the inner dictionaries.
            pid = paper_item.get('id')
            if pid not in posted_ids:
                target_paper = paper_item
                print(f"Selected Top Unposted Paper: {target_paper['title']} (Upvotes: {target_paper.get('upvotes', 'N/A')})")
                break
            else:
                print(f"Skipping duplicate: {paper_item.get('title')} (ID: {pid})")
                
    if not target_paper and papers:
        # Fallback logic also needs duplicate check
        print("No new CV papers found. Checking trending papers...")
        # papers list items still have 'paper' wrapper? 
        # Yes, fetch_daily_papers result is passed to filter_cv_papers but 'papers' var is original list.
        papers.sort(key=lambda x: x.get('paper', {}).get('upvotes', 0), reverse=True)
        
        for paper_wrapper in papers:
            paper_details = paper_wrapper.get('paper', {})
            pid = paper_details.get('id')
            if pid and pid not in posted_ids:
                target_paper = paper_details
                print(f"Top Paper (Fallback): {target_paper.get('title', 'Unknown')} (Upvotes: {target_paper.get('upvotes', 'N/A')})")
                break
    
    if target_paper:
        try:
            content = generate_blog_post(target_paper)
            save_post(target_paper, content)
        except Exception as e:
            print(f"Failed to generate/save post: {e}")
    else:
        print("No new papers found to post.")

if __name__ == "__main__":
    main()
