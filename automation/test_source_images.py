from types import SimpleNamespace
from unittest import mock

import daily_trend_bot as bot


def test_extracts_lazy_responsive_images_and_captions():
    page = '''<article>
    <figure><img src="/placeholder.gif" data-src="/photo.jpg" alt="Product">
    <figcaption>Product in use</figcaption></figure>
    <picture><source srcset="/small.webp 400w, /large.webp 1600w">
    <img src="/fallback.jpg"></picture>
    </article>'''
    response = SimpleNamespace(status_code=200, headers={'content-type': 'text/html'},
                               text=page, url='https://example.org/news/release')
    with mock.patch.object(bot.requests, 'get', return_value=response):
        images = bot._article_image_candidates({'url': response.url})
    assert [x['url'] for x in images] == [
        'https://example.org/photo.jpg', 'https://example.org/large.webp']
    assert images[0]['caption'] == 'Product in use'


def test_placement_uses_real_headings_without_dropping_images_or_touching_code():
    code = '```markdown\n## Example heading\n```'
    content = '## Introduction\nLead\n' + code + '\n' + '\n'.join(
        f'## Section {i}\nBody\n' for i in range(5)
    ) + '\n## 자주 묻는 질문\nFAQ\n'
    images = [{'path': f'https://example.org/{i}.jpg'} for i in range(5)]
    output = bot.insert_source_images(content, images + images[:1])
    assert code in output
    assert output.count('<figure class="news-source-image">') == 5
    assert output.index('<figure') > output.index('Lead')
    for image in images:
        assert output.count(image['path']) == 1
    assert '<figure' not in output.split('## 자주 묻는 질문')[1]
