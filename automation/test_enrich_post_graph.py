from pathlib import Path

from tools import enrich_post_graph as graph


def test_incremental_repairs_unselected_invalid_blocks(tmp_path):
    posts_dir = tmp_path / '_posts'
    posts_dir.mkdir()
    ids = [f'2026-09-01-python-guide-{i}' for i in range(6)]
    for i, post_id in enumerate(ids):
        targets = [target for target in ids if target != post_id][:3]
        if i == 0:
            targets = targets[:2]
        if i == 5:
            targets = []
        body = 'Article body must stay unchanged.\n\n'
        if targets:
            body += '<!-- internal-links:start -->\n' + '\n'.join(
                f'- [Related]({{% post_url {target} %}})' for target in targets
            ) + '\n<!-- internal-links:end -->\n'
        (posts_dir / f'{post_id}.md').write_text(
            f'---\ntitle: Python guide {i}\nsummary: Python programming examples\n'
            'tags: [python]\ncategories: [programming]\n---\n' + body
        )
    posts = graph.load_posts(tmp_path)
    existing, invalid = graph.existing_related_map(posts)
    assert invalid == {ids[0], ids[5]}
    related, touched, _ = graph.build_incremental_related_map(posts, {ids[5]})
    graph.validate_related_map(posts, related, require_coverage=False)
    assert {ids[0], ids[5]} <= touched
    for source in set(existing) - touched:
        assert related[source] == existing[source]
    old = next(post for post in posts if post.post_id == ids[0])
    by_id = {post.post_id: post for post in posts}
    updated, _ = graph.update_link_block_only(old, [by_id[x] for x in related[ids[0]]])
    assert graph.LINK_BLOCK.sub('', updated) == graph.LINK_BLOCK.sub('', old.raw)


def test_post_without_specific_tag_overlap_still_gets_related_links(tmp_path):
    # 브랜드 태그 대부분이 BROAD_RELATED_TAGS 라서, 거버넌스 뉴스처럼 브랜드 태그만
    # 붙은 글은 어느 글과도 tier 0 이 된다. 예전에는 여기서 예외가 나 이미 다 쓴
    # 글이 발행되지 못하고 버려졌다.
    posts_dir = tmp_path / '_posts'
    posts_dir.mkdir()
    ids = [f'2026-09-01-python-guide-{i}' for i in range(4)]
    for i, post_id in enumerate(ids):
        (posts_dir / f'{post_id}.md').write_text(
            f'---\ntitle: Python guide {i}\nsummary: Python programming examples\n'
            'tags: [python]\ncategories: [programming]\n---\nBody.\n'
        )
    lonely_id = '2026-09-22-global-oversight-call'
    (posts_dir / f'{lonely_id}.md').write_text(
        '---\ntitle: Global oversight call\nsummary: Twenty two leaders sign\n'
        'tags: [governance]\ncategories: [policy]\n---\nBody.\n'
    )

    posts = graph.load_posts(tmp_path)
    source = next(post for post in posts if post.post_id == lonely_id)
    signals = graph.build_signal_cache(posts, [p for p in posts if p.is_public])
    assert all(
        signals[(lonely_id, p.post_id)][0] == 0
        for p in posts
        if p.post_id != lonely_id
    )

    selected = graph.select_related(source, posts, signals=signals)
    assert len(selected) == graph.RELATED_COUNT
    assert lonely_id not in {post.post_id for post in selected}

    related_map = graph.build_related_map(posts)
    graph.validate_related_map(posts, related_map, require_coverage=False)
