#!/usr/bin/env python3
"""Prepare reviewable social drafts from published metadata; never send them."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote, urlencode, urlsplit, urlunsplit, parse_qsl

import yaml

ROOT = Path(__file__).resolve().parents[1]


def tracked_url(url: str, platform: str, campaign: str) -> str:
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.startswith('utm_')]
    query += [('utm_source', platform), ('utm_medium', 'social'),
              ('utm_campaign', campaign), ('utm_content', 'answer-first')]
    return urlunsplit(parts._replace(query=urlencode(query)))


def build_pack(post: Path) -> dict:
    raw = post.read_text(encoding='utf-8')
    match = re.match(r'\A---\s*\n(.*?)\n---\s*\n', raw, re.S)
    if not match:
        raise ValueError('Post requires YAML front matter')
    data = yaml.safe_load(match.group(1))
    if data.get('published') is False or data.get('draft') is True:
        raise ValueError('Draft/hidden posts must not be promoted')
    title = str(data.get('title') or '').strip()
    answer = str(data.get('summary') or data.get('description') or '').strip()
    if not title or not answer:
        raise ValueError('Title and description/summary are required')
    slug = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', post.stem)
    permalink = data.get('permalink')
    if permalink:
        if not str(permalink).startswith('/') or str(permalink).startswith('//'):
            raise ValueError('Permalink must be a local absolute path')
        url = 'https://www.opsoai.com' + str(permalink)
    else:
        # Automatic publishers produce these safe slugs. Do not guess Jekyll's
        # normalization for other filenames; supply their explicit permalink.
        if not re.fullmatch(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*', slug):
            raise ValueError('Nonstandard slug: specify the actual permalink')
        url = 'https://www.opsoai.com/posts/' + quote(slug) + '/'
    campaign = 'post-' + post.stem[:10] + '-' + hashlib.sha256(url.encode()).hexdigest()[:8]
    drafts = {}
    for platform in ('threads', 'linkedin'):
        link = tracked_url(url, platform, campaign)
        drafts[platform] = {
            'url': link,
            'text': f'{title}\n\n{answer}\n\n근거와 적용 조건을 정리했습니다.\n{link}',
        }
    return {'post': post.name, 'canonical_url': url, 'status': 'draft',
            'review': '원문 공개, 문맥, 최신 제공 조건을 확인한 뒤 직접 게시하세요.',
            'drafts': drafts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--post', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pack = build_pack(args.post)
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / (args.post.stem + '.json')
    destination.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = [f"# {pack['post']}", '', pack['review'], '']
    for platform, draft in pack['drafts'].items():
        lines += [f'## {platform}', '', draft['text'], '']
    destination.with_suffix('.md').write_text('\n'.join(lines), encoding='utf-8')
    print(f'Distribution drafts: {destination}')


if __name__ == '__main__':
    main()
