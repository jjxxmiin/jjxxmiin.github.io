from pathlib import Path
import re
import struct

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_post_layout_keeps_one_url_and_builds_semantic_pages():
    layout = _read("_layouts/post.html")

    assert "content | split: '<h2'" in layout
    assert 'data-book-kind="cover"' in layout
    assert 'data-book-kind="chapter"' in layout
    assert 'data-book-kind="finish"' in layout
    assert "{{ book_sections | first }}" in layout
    assert "<h2{{ section }}" in layout
    assert '<template data-book-scroll-ad-template>' in layout
    assert "google-ad-post-inline.html lazy=true" in layout
    assert "google-ad-post-bottom.html" in layout
    assert "'/assets/js/book-reader.js'" in layout
    assert "data-book-announcer" not in layout
    assert "data-book-start" not in layout
    assert 'class="book-afterword-panel"' in layout
    assert 'id="book-afterword" hidden' in layout


def test_reader_has_accessible_fallbacks_and_navigation():
    script = _read("assets/js/book-reader.js")
    styles = _read("_sass/_book-reader.scss")
    head = _read("_includes/head.html")
    layout = _read("_layouts/post.html")

    assert "hidden', 'until-found'" in script
    assert "beforematch" in script
    assert "prefers-reduced-motion" in script
    assert "ArrowRight" in script and "ArrowLeft" in script
    assert "pointerdown" in script and "pointerup" in script
    assert "paginateContent" in script
    assert "splitLongLists" in script and "splitLongTables" in script
    assert "splitLongCallouts" in script
    assert "projectCard" in script and "content.insertBefore(projectCard" in script
    assert "block.matches('.proj')" in script
    assert "heading && groupIndex === 0" in script
    assert "headingTemplate.cloneNode" not in script
    assert "book-prologue-part-" not in script
    assert "heading ? heading.id : 'book-page-'" in script
    assert "renderMermaids" in script
    assert "fitCoverTitle" in script
    assert "book-afterword-open" in script
    assert "initializeBookAds" in script
    assert "ensureScrollAd" in script
    assert "syncAfterword" in script
    assert "book_page_view" in script and "book_complete" in script
    assert 'aria-controls="book-afterword"' in layout
    assert 'aria-expanded="false"' in layout
    assert "@media print" in styles
    assert "@media (max-width: 767.98px)" in styles
    assert "book-js" in head
    assert "--book-marker" in styles
    assert ":where(p, li, blockquote, figcaption) strong" in styles


def test_reader_is_exactly_one_dynamic_viewport_and_opens_desktop_spreads():
    script = _read("assets/js/book-reader.js")
    styles = _read("_sass/_book-reader.scss")

    assert "height: 100dvh" in styles
    assert "body.book-page .mermaidTooltip" in styles
    assert ":not(.book-afterword-ready) #tail-wrapper.book-tail" in styles
    assert "grid-template-rows: 3rem 2px minmax(0, 1fr)" in styles
    assert ".book-page-button-prev" in styles
    assert ".book-page-button-next" in styles
    assert "@media (min-width: 1024px)" in styles
    assert "spreadBounds" in script
    assert "paginationKey" in script and "window.location.reload()" in script
    assert "window.innerHeight <= 650 ? 1 : 3" in script
    assert "is-spread-left" in script and "is-spread-right" in script
    assert "02–03" not in script  # the range is calculated, never hard-coded


def test_post_pages_use_immersive_main_without_the_legacy_toc_panel():
    default = _read("_layouts/default.html")
    styles_entry = _read("assets/css/jekyll-theme-chirpy.scss")

    assert "class=\"book-page\"" in default
    assert "{% unless page.layout == 'post' %}" in default
    assert "@use 'book-reader';" in styles_entry


def test_site_uses_the_noonnu_brand_type_system():
    head = _read("_includes/head.html")
    fonts = _read("_includes/font-opsoai.html")
    chart = _read("assets/lib/chartjs/chart-render.js")

    assert "font-opsoai.html" in head
    assert "Paperlogy-8ExtraBold.woff2" in fonts
    assert "SUIT-Regular.woff2" in fonts
    assert "SUIT-Medium.woff2" in fonts
    assert "SUIT-Bold.woff2" in fonts
    assert "--opsoai-font-display" in fonts
    assert "SUIT, sans-serif" in chart


def test_visual_book_images_are_social_only_and_never_render_as_thumbnails():
    config = yaml.safe_load(_read("_config.yml"))
    home = _read("_layouts/home.html")
    layout = _read("_layouts/post.html")
    assert config.get("cdn") is None
    assert "post.image" not in home
    assert "page.image" not in layout
    assert "page.cover_photo" in layout
    assert 'class="book-cover-photo"' in layout
    assert "book-cover-graphic" not in layout
    assert "page.title | replace: '·', ', '" in layout
    assert "book-prologue-image" not in layout

    names = (
        "ai-youth-jobs-career-ladder",
        "ai-productivity-paradox",
        "deepfake-proof-collapse",
        "ai-tools-100-directory",
    )
    for name in names:
        post = _read(f"_posts/2026-09-03-{name}.md")
        image_path = ROOT / "assets" / "img" / "visual-books" / f"{name}.png"
        cover_path = ROOT / "assets" / "img" / "visual-books" / f"{name}-cover-photo.webp"
        assert f"path: /assets/img/visual-books/{name}.png" in post
        assert f"path: /assets/img/visual-books/{name}-cover-photo.webp" in post
        with image_path.open("rb") as image:
            assert image.read(8) == b"\x89PNG\r\n\x1a\n"
            image.seek(16)
            assert struct.unpack(">II", image.read(8)) == (1200, 630)
        assert cover_path.stat().st_size > 20_000


def test_ads_stay_out_of_paged_reading_and_lazy_load_after_completion():
    layout = _read("_layouts/post.html")
    home = _read("_layouts/home.html")
    script = _read("assets/js/book-reader.js")
    bottom_ad = _read("_includes/google-ad-post-bottom.html")

    assert 'data-book-kind="ad"' not in layout
    assert "Math.floor(contentPages.length * 0.45)" in script
    assert "syncAfterword(bounds.end === pages.length - 1)" in script
    assert "data-book-ad-requested" in script
    assert "(window.adsbygoogle = window.adsbygoogle || []).push({});" not in bottom_ad
    assert 'data-book-ad-placement="afterword"' in bottom_ad
    assert "visible_post_index == 4" in home


def test_collection_directory_has_exactly_one_hundred_unique_official_links():
    post = _read("_posts/2026-09-03-ai-tools-100-directory.md")

    assert "collection: true" in post
    assert len(re.findall(r"^## ", post, flags=re.MULTILINE)) == 11  # quick picker plus ten categories
    assert post.count("**추천:**") == 100


def test_faq_and_publication_details_are_visible_in_the_book():
    layout = _read("_layouts/post.html")
    script = _read("assets/js/book-reader.js")
    styles = _read("_sass/_book-reader.scss")

    assert 'class="book-page book-content-page book-faq-page"' in layout
    assert "item.question | strip_html | escape" in layout
    assert "item.answer | markdownify" in layout
    assert 'class="book-publication-meta"' in layout
    assert 'rel="author"' in layout
    assert "book_chapter_count" in layout
    assert "wireFaqs" in script
    assert "details.book-faq-item[open]" in script
    assert ".book-faq-item" in styles
    assert ".book-publication-meta" in styles


def test_manim_math_visual_has_video_and_static_fallback():
    post = _read("_posts/2026-09-03-ai-youth-jobs-career-ladder.md")
    video = ROOT / "assets" / "media" / "manim" / "ratio-268-of-285.mp4"
    poster = ROOT / "assets" / "media" / "manim" / "ratio-268-of-285-poster.png"

    assert "/assets/media/manim/ratio-268-of-285.mp4" in post
    assert "/assets/media/manim/ratio-268-of-285-poster.png" in post
    assert video.stat().st_size > 100_000
    with poster.open("rb") as image:
        assert image.read(8) == b"\x89PNG\r\n\x1a\n"
        image.seek(16)
        assert struct.unpack(">II", image.read(8)) == (1920, 1080)
