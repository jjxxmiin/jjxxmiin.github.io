from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from tools.build_distribution_pack import build_pack, tracked_url


def test_pack_reuses_verified_description_and_links_back(tmp_path):
    p = tmp_path / '2026-09-13-news-example.md'
    p.write_text('---\ntitle: New feature\ndescription: Available in preview only.\n---\nBody')
    pack = build_pack(p)
    assert pack['status'] == 'draft'
    for platform, draft in pack['drafts'].items():
        assert 'Available in preview only.' in draft['text']
        url = urlsplit(draft['url'])
        assert url.path == '/posts/news-example/'
        assert parse_qs(url.query)['utm_source'] == [platform]
        assert parse_qs(url.query)['utm_medium'] == ['social']


def test_tracking_replaces_old_tags_preserves_other_query_and_fragment():
    result = tracked_url('https://www.opsoai.com/posts/a/?view=full&utm_source=old#faq', 'threads', 'a')
    parts = urlsplit(result)
    assert parts.fragment == 'faq'
    assert parse_qs(parts.query)['view'] == ['full']
    assert parse_qs(parts.query)['utm_source'] == ['threads']


def test_hidden_post_cannot_create_draft(tmp_path):
    p = tmp_path / '2026-09-13-hidden.md'
    p.write_text('---\ntitle: Hidden\ndescription: Private\npublished: false\n---\nBody')
    with pytest.raises(ValueError, match='hidden'):
        build_pack(p)
