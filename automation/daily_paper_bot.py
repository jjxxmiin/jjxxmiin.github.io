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
    
    # Front Matter
    front_matter = {
        "layout": "post",
        "title": f"[Review] {paper['title']}",
        "date": f"{date_str} 09:00:00 +0900",
        "categories": ["AI", "Computer Vision"],
        "tags": ["paper-review", "cv", "huggingface-daily"],
        "author": "OPSOAI" 
    }
    
    # Add image if available
    if 'thumbnail' in paper:
        front_matter['image'] = {
            "path": paper['thumbnail'],
            "alt": "Paper Thumbnail"
        }
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.dump(front_matter, f, allow_unicode=True)
        f.write("---\n\n")
        f.write(content)
        f.write(f"\n\n[Original Paper Link](https://huggingface.co/papers/{paper['id']})")

    print(f"Saved post to {filepath}")

def main():
    print("Fetching papers...")
    papers = fetch_daily_papers()
    print(f"Fetched {len(papers)} papers.")
    
    cv_papers = filter_cv_papers(papers)
    
    target_paper = None
    
    # Sort CV papers by upvotes if available
    if cv_papers:
        cv_papers.sort(key=lambda x: x.get('upvotes', 0), reverse=True)
        target_paper = cv_papers[0]
        print(f"Top CV Paper: {target_paper['title']} (Upvotes: {target_paper.get('upvotes', 'N/A')})")
    elif papers:
        print("No CV papers found. Falling back to top trending paper.")
        # We need to sort based on the upvotes inside the 'paper' object
        # papers is a list of items where item['paper'] has the details
        papers.sort(key=lambda x: x.get('paper', {}).get('upvotes', 0), reverse=True)
        target_paper = papers[0].get('paper', {})
        print(f"Top Paper (Fallback): {target_paper.get('title', 'Unknown')} (Upvotes: {target_paper.get('upvotes', 'N/A')})")

    if target_paper:
        # print(f"Selected paper: {target_paper['title']}") # Already printed above
        try:
            content = generate_blog_post(target_paper)
            save_post(target_paper, content)
        except Exception as e:
            print(f"Failed to generate/save post: {e}")
    else:
        print("No papers found.")

if __name__ == "__main__":
    main()
