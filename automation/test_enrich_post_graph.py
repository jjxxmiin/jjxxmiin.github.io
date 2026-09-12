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
