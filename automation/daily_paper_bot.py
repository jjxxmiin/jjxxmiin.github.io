import os
import datetime
import shutil
from bs4 import BeautifulSoup
import requests
from google import genai
from google.genai import types
import yaml

# Configuration
HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"
ARXIV_HTML_URL = "https://arxiv.org/html"
POSTS_DIR = "../_posts"
IMAGE_DIR = "../assets/img/papers"
FALLBACK_THUMBNAIL = "/assets/img/logo.png"


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

def extract_arxiv_info(paper_id):
    """Extracts figures and captions from Arxiv HTML page."""
    url = f"{ARXIV_HTML_URL}/{paper_id}"
    try:
        print(f"Fetching Arxiv page: {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        figures = []
        
        # Arxiv HTML usually puts figures in <figure class="ltx_figure">
        for fig in soup.find_all('figure', class_='ltx_figure'):
            img_tag = fig.find('img')
            if not img_tag:
                continue
                
            img_src = img_tag.get('src')
            if not img_src:
                continue
            
            # Construct absolute URL
            # img_src is usually relative like 'x1.png'
            full_img_url = f"{url}/{img_src}"
            
            caption_tag = fig.find('figcaption')
            caption = caption_tag.get_text(strip=True) if caption_tag else ""
            
            figures.append({
                'url': full_img_url,
                'src_filename': img_src,
                'caption': caption
            })
            
        print(f"Found {len(figures)} figures.")
        return figures
        
    except Exception as e:
        print(f"Error extracting Arxiv info: {e}")
        return None

def download_images(images, paper_id):
    """Downloads images to local assets directory."""
    local_images = []
    
    # Create target directory
    target_dir = os.path.join(IMAGE_DIR, paper_id)
    os.makedirs(target_dir, exist_ok=True)
    
    for i, img_data in enumerate(images):
        # Limit to top 5 images to avoid clutter
        if i >= 5:
            break
            
        img_url = img_data['url']
        src_filename = img_data['src_filename']
        
        # Ensure filename is safe or just use index if weird
        # Arxiv usually names them x1.png, x2.png etc. 
        # But let's prefix with paper_id just in case or keep structure
        filename = f"{src_filename}"
        save_path = os.path.join(target_dir, filename)
        
        # Web accessible path for Jekyll
        web_path = f"/assets/img/papers/{paper_id}/{filename}"
        
        try:
            # Ensure the parent directory of the save_path exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            print(f"Downloading {img_url} to {save_path}...")
            r = requests.get(img_url, stream=True)
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
            
            local_images.append({
                'path': web_path,
                'caption': img_data['caption']
            })
        except Exception as e:
            print(f"Failed to download image: {e}")
            
    return local_images

def generate_blog_post(paper, images=None):
    """Generates a blog post using Gemini with JSON structured output."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    
    client = genai.Client(api_key=api_key)
    model_id = "gemini-3-flash-preview" 

    # Format images for the prompt
    images_text = "No images available."
    if images:
        images_text = "Available Images (You MUST use these in the blog post where contextually appropriate using the format `![Caption](Path)`):\n"
        for img in images:
            images_text += f"- Caption: {img['caption']}\n  Path: {img['path']}\n"

#     prompt_text = f"""
# **Role & Persona:**
# You are a Senior Chief AI Scientist and a renowned Technical Columnist for a top-tier tech blog.
# Your goal is to write a **comprehensive, authoritative, and deeply technical analysis** of the provided research paper in **Korean**.

# **Input Data:**
# - Paper Title: {paper['title']}
# - Paper Abstract: {paper['summary']}
# - Paper URL: https://huggingface.co/papers/{paper['id']}
# - {images_text}

# **Critical Constraints & Guidelines:**
# 1.  **Extreme Depth & Length**: Aim for **3,000+ words**.
# 2.  **Professional Tone**: Use a formal, expert tone (e.g., "~합니다/습니다" style).
# 3.  **Detailed Structure**:
#     -   **SEO-Optimized Title**: A compelling Korean title.
#     -   **Front Matter Summary**: A concise (under 50 chars), catchy, and suitable summary for the blog post preview (Front Matter).
#     -   **Content**: The full blog post content in Markdown, following the structure:
#         1.  Executive Summary (핵심 요약)
#         2.  Introduction & Problem Statement (연구 배경 및 문제 정의)
#         3.  Core Methodology (핵심 기술 및 아키텍처 심층 분석)
#         4.  Implementation Details & Experiment Setup (구현 및 실험 환경)
#         5.  Comparative Analysis (성능 평가 및 비교)
#         6.  Real-World Application & Impact (실제 적용 분야 및 글로벌 파급력) - **Crucial Section**: Discuss practical use cases.
#         7.  Discussion: Limitations & Critical Critique (한계점 및 기술적 비평) - **Be critical**.
#         8.  Conclusion (결론 및 인사이트)
#         9.  Expert's Touch (전문가의 시선) - **CRUCIAL NEW SECTION**: Add an "Expert's Touch" section. It must contain a sharp 1-line comment, technical limitations, and practical/open-source application points from a computer engineering researcher's perspective.

# **High CPC Keyword Optimization (CRITICAL):**
# - Naturally integrate high-value computing and business keywords throughout the text. These keywords must sound completely natural in the context of the paper's application and system architecture.

# **Image Placement Instructions:**
# -   You have been provided with a list of available images with their local paths.
# -   **CRITICAL**: You MUST insert these images into the **Content** body where they are most relevant to the text.
# -   Do not dump them all at the beginning or end. Place them near the text that describes them.
# -   Use the exact path provided. Format: `![Caption](Path)`
# -   Add a short italicized caption below the image as well.

# **Negative Constraints (CRITICAL):**
# 1.  **Final Polish Only**: The output must be the final, publication-ready article, not a draft or a thinking process.
# 2.  **Math Formatting**: If using mathematical notation, use standard LaTeX within dollar signs (e.g., $E = mc^2$) so it renders correctly if supported, or use clear text representation. Avoid raw, broken LaTeX syntax.

# **Action:**
# 1.  **Be Opinionated**: Don't just translate/summarize. Add your expert insight ("This is similar to X, but better because Y").
# 2.  **Add Value**: Explain *why* this matters to a developer or business.
# 3.  Generate the blog post adhering to the JSON schema provided.
# """

    prompt_text = f"""
    **Role & Persona:**
    You are a Computer Engineering Ph.D. Researcher and the Technical Lead of an AI startup. 
    Your goal is to write a highly technical, yet commercially insightful analysis of the provided AI research paper in Korean for a top-tier tech blog.

    **Input Data:**
    - Paper Title: {paper['title']}
    - Paper Abstract: {paper['summary']}
    - Paper URL: https://huggingface.co/papers/{paper['id']}
    - Available Images: {images_text}

    **Critical Constraints & Guidelines:**
    1.  **Density over Fluff**: Write a comprehensive, in-depth analysis. Do NOT generate repetitive fluff just to reach a specific word count. Base your technical insights strictly on the provided abstract and logically infer the standard methodologies used.
    2.  **Professional Tone**: Use a formal, analytical, and expert tone ("~합니다/습니다", "~이다/한다" style, suitable for a professional tech column).
    3.  **SEO & High CPC Optimization**: Naturally integrate high-value technical and business keywords (e.g., B2B AI SaaS, Model Optimization, Cloud Infrastructure, Edge Computing, Tech Investment) ONLY where contextually relevant, especially in the practical application section.
    4.  **Content Structure (Strict Outline)**:
        -   **Title**: Catchy, SEO-optimized Korean title (Include English tech terms if necessary).
        -   **Front Matter**: 1-2 sentence compelling hook for the blog preview.
        -   **[1] Executive Summary**: Clear, bulleted TL;DR of the paper's core contribution.
        -   **[2] Research Background & Problem Statement**: Why is this research necessary in the current AI landscape?
        -   **[3] Core Methodology & Architecture**: Deep dive into the proposed solution. Explain the algorithms or system architecture intuitively.
        -   **[4] Practical Application & Market Impact**: How can this technology be commercialized? Discuss specific use cases for startups or enterprise environments.
        -   **[5] Expert's Touch (Critique & Implementation)**: From a computer engineering and startup founder's perspective, provide:
            - A sharp 1-line verdict on the paper.
            - Technical limitations or scaling challenges.
            - Practical tips for developers looking to implement this, build a pipeline around it, or find open-source equivalents.

    **Image Placement Rules:**
    -   Insert provided images seamlessly within the text (especially in Section 3 or 4) using exact paths: `![Caption](Path)`
    -   Add a brief, italicized technical caption below each image. 
    -   Distribute images logically; do not cluster them together.

    **Negative Constraints (CRITICAL):**
    -   Output ONLY the final Markdown content. Do not include introductory conversational text (e.g., "Here is the blog post").
    -   Do not hallucinate specific quantitative experimental results unless explicitly stated in the abstract.
    -   If using mathematical notation, use standard LaTeX within `$ $` or `$$ $$` (e.g., $E = mc^2$). Do not use raw LaTeX syntax outside these delimiters.
    """
    # prompt_text = f"""
    # **Role & Persona:**
    # You are a Computer Engineering Ph.D. Researcher and the Technical Lead of an AI startup. 
    # Your goal is to write a highly technical, yet commercially insightful analysis of the provided AI research paper in Korean. The output MUST be strictly optimized for Google SEO and Google AdSense High CPC monetization.

    # **Input Data:**
    # - Paper Title: {paper['title']}
    # - Paper Abstract: {paper['summary']}
    # - Paper URL: https://huggingface.co/papers/{paper['id']}
    # - Available Images: {images_text}

    # **Critical SEO & AdSense Revenue Constraints:**
    # 1.  **High CPC Keyword Integration (CRITICAL)**: To maximize AdSense revenue, you MUST naturally weave in high-value commercial keywords relevant to the AI/Tech industry. 
    #     -   *Target Keywords*: Cloud Computing (클라우드 컴퓨팅, AWS, GCP, Azure), Enterprise AI Solutions (기업용 AI 솔루션, B2B SaaS), Infrastructure Optimization (인프라 최적화, GPU 서버 호스팅 비용 절감), Data Security (데이터 보안 및 컴플라이언스), ROI/Investment (AI 도입 ROI, 기술 투자).
    #     -   *Placement*: Integrate these strictly within the 'Practical Application' and 'Expert's Touch' sections when discussing commercialization, scaling, or deployment. Do not make it look like spam.
    # 2.  **Google SEO Optimization**:
    #     -   Identify 3-4 primary specific technical keywords from the abstract. Place them in the Title, the first paragraph, and H2 headings.
    #     -   Use short paragraphs (max 3-4 sentences), bullet points, and **bold text** for key concepts to increase dwell time.
    # 3.  **Density over Fluff**: Extract maximum technical value from the abstract and infer standard architectures. Do NOT generate repetitive fluff. Use a formal, analytical tone ("~합니다/습니다").

    # **Content Structure (Strict Outline):**
    # -   **Title (H1)**: A highly clickable, SEO-optimized Korean title (Include English tech terms/model names).
    # -   **Meta Description (Front Matter)**: Exactly 1-2 sentences (under 150 characters) summarizing the core value with primary keywords. Format: `> **Meta Description:** [Text]`
    # -   **[1] 핵심 요약 (Executive Summary) (H2)**: Bulleted TL;DR of the paper's core contribution and metrics.
    # -   **[2] 연구 배경 및 문제 정의 (Background) (H2)**: Why is this research necessary? What bottleneck does it solve?
    # -   **[3] 핵심 기술 및 아키텍처 심층 분석 (Core Methodology) (H2)**: Deep dive into the proposed solution. (Use H3 `###` for sub-components).
    # -   **[4] 기업 적용 및 비즈니스 임팩트 (Practical Application) (H2)**: **[CRITICAL FOR ADSENSE]** How can this be commercialized? Discuss specific use cases for enterprise environments, B2B SaaS integration, cloud infrastructure cost reduction, or GPU hosting efficiency.
    # -   **[5] 전문가의 시선 (Expert's Touch) (H2)**: From a tech lead's perspective:
    #     -   A sharp 1-line verdict.
    #     -   Technical limitations (e.g., scaling on cloud, data security).
    #     -   Practical tips for developers (open-source equivalents).

    # **Image Placement & SEO Rules:**
    # -   Insert provided images seamlessly within the text using the exact paths.
    # -   **CRITICAL SEO**: Generate descriptive, keyword-rich Alt Text for every image. Format: `![SEO-optimized descriptive Alt Text in Korean](Path)`
    # -   Add a brief, italicized technical caption below each image.

    # **Negative Constraints:**
    # -   Output ONLY the final Markdown content. No conversational intro/outro.
    # -   Do not hallucinate specific quantitative experimental results unless explicitly stated.
    # -   For math, use standard LaTeX within `$ $` or `$$ $$`.
    # """

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "The SEO-optimized Korean title of the blog post."},
            "summary": {"type": "STRING", "description": "A concise, catchy summary (under 50 chars) for the front matter."},
            "content": {"type": "STRING", "description": "The full blog post content in Markdown format."}
        },
        "required": ["title", "summary", "content"]
    }

    tools = [
        types.Tool(google_search=types.GoogleSearch())
    ]
    
    generate_content_config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
        ),
        tools=tools,
        response_mime_type="application/json",
        response_schema=response_schema
    )
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt_text),
            ],
        ),
    ]

    print("Generating content with Gemini (JSON mode)...")
    # Non-streaming for JSON usually safer to ensure complete valid JSON, but stream is fine if we concat.
    # However, for JSON mode, non-streaming is often simpler.
    response = client.models.generate_content(
        model=model_id,
        contents=contents,
        config=generate_content_config,
    )
    
    # Check if response has text (it should be JSON string)
    if response.text:
        import json
        try:
             # Parse JSON
             return json.loads(response.text)
        except json.JSONDecodeError as e:
             print(f"Failed to parse JSON response: {e}")
             print(f"Raw response: {response.text[:200]}...")
             return None
    return None

def save_post(paper, post_data, images=None):
    """Saves the blog post to the _posts directory."""
    if not post_data:
        print("No post data to save.")
        return

    # Use US Eastern Time (UTC-5)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    us_time = utc_now - datetime.timedelta(hours=5) # approximated EST
    date_str = us_time.strftime("%Y-%m-%d")
    
    # Sanitize title for filename
    safe_title = "".join([c if c.isalnum() else "-" for c in paper['title']]).strip("-")
    filename = f"{date_str}-{safe_title}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    
    # Extract fields from JSON
    # post_data is expected to be a dict: {'title': ..., 'summary': ..., 'content': ...}
    korean_title = post_data.get('title', paper['title'])
    summary = post_data.get('summary', '최신 Computer Vision 논문 리뷰')
    content_body = post_data.get('content', '')
    
    # Fix double-escaped newlines from Gemini API JSON response
    # The API sometimes returns \\n instead of actual newlines
    if '\\n' in content_body:
        content_body = content_body.replace('\\n', '\n')

    # Front Matter
    front_matter = {
        "layout": "post",
        "title": f"[{paper.get('publishedAt', date_str)[:10]}] {korean_title}",
        "date": date_str, # YYYY-MM-DD
        "categories": "tech", 
        "math": True,
        "summary": summary
    }

    # Add image if available or fallback
    image_path = paper.get('thumbnail', FALLBACK_THUMBNAIL)
    if image_path:
         front_matter['image'] = {
            "path": image_path,
            "alt": "Paper Thumbnail"
        }
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("---\n")
            yaml.dump(front_matter, f, allow_unicode=True, sort_keys=False)
            f.write("---\n\n")
            
            f.write(content_body)
            
            # Check if images were used in the content, if not, add them at the bottom
            if images:
                unused_images = [img for img in images if img['path'] not in content_body]
                if unused_images:
                    f.write("\n\n## Additional Figures\n")
                    for img in unused_images:
                        f.write(f"\n![{img['caption']}]({img['path']})\n")
                        f.write(f"*{img['caption']}*\n")

            f.write(f"\n\n[Original Paper Link](https://huggingface.co/papers/{paper['id']})")
        print(f"Saved post to {filepath}")
    except Exception as e:
        print(f"Error writing file {filepath}: {e}")

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
    extracted_images = [] # Store extracted images to pass later
    
    # Sort CV papers by upvotes
    if cv_papers:
        # Sort based on inner upvotes
        cv_papers.sort(key=lambda x: x.get('upvotes', 0), reverse=True)
        
        # Iterate and find first one not posted AND accessible
        for paper_item in cv_papers:
            pid = paper_item.get('id')
            if pid not in posted_ids:
                print(f"Checking candidate: {paper_item['title']} (Upvotes: {paper_item.get('upvotes', 'N/A')})")
                
                # Check accessibility first!
                print(f"Attempting to verify Arxiv for {pid}...")
                current_extracted_images = extract_arxiv_info(pid)
                
                if current_extracted_images is None:
                    print(f"Skipping {pid}: Cannot access Arxiv HTML (404/Error).")
                    continue
                
                # If valid, select this paper
                target_paper = paper_item
                extracted_images = current_extracted_images
                print(f"Selected Paper: {target_paper['title']}")
                break
            else:
                print(f"Skipping duplicate: {paper_item.get('title')} (ID: {pid})")
                
    if not target_paper and papers:
        # Fallback logic also needs accessibility check
        print("No new CV papers found (or all failed). Checking all trending papers...")
        papers.sort(key=lambda x: x.get('paper', {}).get('upvotes', 0), reverse=True)
        
        for paper_wrapper in papers:
            paper_details = paper_wrapper.get('paper', {})
            pid = paper_details.get('id')
            if pid and pid not in posted_ids:
                print(f"Checking fallback candidate: {paper_details.get('title', 'Unknown')} (Upvotes: {paper_details.get('upvotes', 'N/A')})")
                
                # Check accessibility
                current_extracted_images = extract_arxiv_info(pid)
                
                if current_extracted_images is None:
                    print(f"Skipping {pid}: Cannot access Arxiv HTML (404/Error).")
                    continue
                
                target_paper = paper_details
                extracted_images = current_extracted_images
                print(f"Selected Fallback Paper: {target_paper.get('title', 'Unknown')}")
                break
    
    if target_paper:
        try:
            # Download images if any
            images = []
            pid = target_paper['id']
            if extracted_images:
                images = download_images(extracted_images, pid)
                
            content = generate_blog_post(target_paper, images)
            save_post(target_paper, content, images)
        except Exception as e:
            print(f"Failed to generate/save post: {e}")
    else:
        print("No accessible new papers found to post.")

if __name__ == "__main__":
    main()
