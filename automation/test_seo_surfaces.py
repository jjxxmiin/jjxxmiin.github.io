from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_head_exposes_search_answer_and_social_metadata():
    head = _read("_includes/head.html")

    assert "max-image-preview:large" in head
    assert "application/atom+xml" in head and "'/feed.xml' | absolute_url" in head
    assert "application/rss+xml" in head and "'/rss.xml' | absolute_url" in head
    assert 'property="article:section"' in head
    assert 'property="article:tag"' in head
    assert "'\"@type\":\"imageObject\"', '\"@type\":\"ImageObject\"'" in head
    assert '"@type": "WebPage"' in head
    assert '"primaryImageOfPage"' in head
    assert '"isAccessibleForFree": true' in head
    assert '"@type": "Organization"' in head
    assert 'name="twitter:image"' in head
    assert 'property="twitter:image"' not in head


def test_sitemaps_only_submit_html_and_visible_editorial_images():
    sitemap = _read("sitemap.xml")
    news = _read("news-sitemap.xml")
    robots = _read("assets/robots.txt")

    assert 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"' in sitemap
    assert "for page in site.html_pages" in sitemap
    assert "post.cover_photo.path" in sitemap
    assert "post.book_visual.path" in sitemap
    assert 'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"' in news
    assert "post.seo.type == 'NewsArticle'" in news
    assert "'/news-sitemap.xml' | absolute_url" in robots


def test_machine_discovery_files_match_the_visual_book_service():
    concise = _read("llms.txt")
    complete = _read("llms-full.txt")
    atom = _read("assets/feed.xml")
    about = _read("about.md")

    assert "짧은 시각 책" in concise
    assert "'/llms-full.txt' | absolute_url" in concise
    assert "site.posts | size" in complete
    assert "post.url | absolute_url" in complete
    assert "<icon>{{ '/assets/img/favicons/favicon.ico' | absolute_url }}</icon>" in atom
    assert "source | replace: '&', '&amp;'" not in atom
    assert "type: AboutPage" in about
