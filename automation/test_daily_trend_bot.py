import datetime
import json
import os
import tempfile
import unittest
from unittest import mock

import yaml

import daily_trend_bot as bot


KST = datetime.timezone(datetime.timedelta(hours=9))


class DailyTrendNewsBotTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.datetime(2026, 7, 26, 9, 0, tzinfo=KST)

    def test_canonical_url_removes_tracking_parameters(self):
        url = bot.canonical_url(
            "HTTP://Example.COM/ai/launch/?utm_source=x&keep=1&fbclid=abc#top"
        )
        self.assertEqual(url, "https://example.com/ai/launch?keep=1")

    def test_direct_source_rejects_search_home_and_image(self):
        self.assertEqual(
            bot.direct_source_rejection_reason("https://news.google.com/search?q=ai"),
            "검색 결과 URL",
        )
        self.assertEqual(
            bot.direct_source_rejection_reason("https://example.com/news"),
            "홈페이지 또는 섹션 URL",
        )
        self.assertEqual(
            bot.direct_source_rejection_reason("https://cdn.example.com/launch.png"),
            "기사/발표 원문이 아닌 파일 URL",
        )
        self.assertIsNone(
            bot.direct_source_rejection_reason(
                "https://example.com/2026/07/new-ai-model-announcement"
            )
        )

    def test_recent_publication_has_strict_window(self):
        self.assertTrue(
            bot.recent_publication("2026-07-25", now=self.now, max_days=7)
        )
        self.assertFalse(
            bot.recent_publication("2026-07-10", now=self.now, max_days=7)
        )
        self.assertFalse(
            bot.recent_publication("unknown", now=self.now, max_days=7)
        )

    @mock.patch.object(bot, "generate_content_with_fallback")
    def test_discovery_executes_full_prompt_and_normalizes_candidates(self, generate):
        generate.return_value = json.dumps([{
            "topic_name": "Example AI",
            "headline": "Example AI releases a verified new model",
            "summary": "The company released a new model.",
            "why_it_matters": "Developers can evaluate a new option.",
            "event_status": "released",
            "published_at": "2026-07-26",
            "source_name": "Example",
            "source_url": "https://example.com/2026/07/new-model?utm_source=test",
            "source_tier": "official",
            "entities": ["Example AI", "Example Model"],
            "search_query": "Example AI new model official announcement",
            "trend_score": 91,
        }])
        with mock.patch.object(bot, "kst_now", return_value=self.now), \
                mock.patch.object(bot, "recent_news_history", return_value=[]):
            candidates = bot.find_trending_topic(mock.Mock())
        self.assertEqual(len(candidates), 1)
        self.assertEqual(
            candidates[0]["source_url"],
            "https://example.com/2026/07/new-model",
        )
        self.assertEqual(candidates[0]["trend_score"], 91)

    def test_duplicate_story_matches_source_but_not_company_name(self):
        history = [{
            "title": "Example의 이전 소식",
            "headline": "Example releases feature A",
            "publishedAt": "2026-07-25",
            "sourceUrls": ["https://example.com/news/feature-a"],
            "entities": ["Example"],
        }]
        duplicate = {
            "headline": "Example releases feature A",
            "published_at": "2026-07-25",
            "source_url": "https://example.com/news/feature-a?utm_source=x",
            "entities": ["Example"],
        }
        new_story = {
            "headline": "Example releases a different model",
            "published_at": "2026-07-26",
            "source_url": "https://example.com/news/different-model",
            "entities": ["Example"],
        }
        self.assertTrue(bot.check_duplication(duplicate, history=history))
        self.assertFalse(bot.check_duplication(new_story, history=history))

    @mock.patch.object(bot, "probe_source")
    @mock.patch.object(bot, "generate_content_with_fallback")
    def test_fact_check_requires_and_normalizes_direct_sources(self, generate, probe):
        first = "https://official.example.com/announcements/new-model"
        second = "https://trusted.example.net/ai/example-new-model"
        generate.return_value = json.dumps({
            "verified": True,
            "reason": "공식 발표와 독립 보도로 확인",
            "event_status": "released",
            "published_at": "2026-07-25",
            "sources": [
                {
                    "url": first,
                    "title": "Official model announcement",
                    "publisher": "Example",
                    "published_at": "2026-07-25",
                    "tier": "official",
                },
                {
                    "url": second,
                    "title": "Example releases a new model",
                    "publisher": "Trusted Tech",
                    "published_at": "2026-07-25",
                    "tier": "trusted",
                },
            ],
            "facts": [
                {"text": f"Verified fact {index}", "source_urls": [first, second]}
                for index in range(1, 5)
            ],
            "unknowns": ["Regional rollout timing is not published."],
        })
        probe.side_effect = lambda url: {
            "url": bot.canonical_url(url),
            "status": 200,
            "reachable": True,
        }
        candidate = {
            "topic_name": "Example AI",
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
            "source_url": first,
            "event_status": "released",
        }
        with mock.patch.object(bot, "kst_now", return_value=self.now):
            evidence = bot.verify_news_candidate(mock.Mock(), candidate)
        self.assertIsNotNone(evidence)
        self.assertEqual(len(evidence["sources"]), 2)
        self.assertEqual(len(evidence["facts"]), 4)
        self.assertEqual(evidence["sources"][0]["tier"], "official")

    @mock.patch.object(bot, "probe_source")
    @mock.patch.object(bot, "generate_content_with_fallback")
    def test_relaxed_fact_check_keeps_single_source_for_daily_fallback(
        self,
        generate,
        probe,
    ):
        source = "https://official.example.com/announcements/new-model"
        generate.return_value = json.dumps({
            "verified": True,
            "reason": "공식 발표 한 건으로 확인",
            "event_status": "released",
            "published_at": "2026-07-25",
            "sources": [{
                "url": source,
                "title": "Official model announcement",
                "publisher": "Example",
                "published_at": "2026-07-25",
                "tier": "official",
            }],
            "facts": [{
                "text": "Example released the model.",
                "source_urls": [source],
            }],
            "unknowns": ["Independent reporting is not available yet."],
        })
        probe.return_value = {
            "url": source,
            "status": 200,
            "reachable": True,
        }
        candidate = {
            "topic_name": "Example AI",
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
            "source_url": source,
            "event_status": "released",
        }
        with mock.patch.object(bot, "kst_now", return_value=self.now):
            evidence = bot.verify_news_candidate(
                mock.Mock(),
                candidate,
                strict=False,
            )
        self.assertIsNotNone(evidence)
        self.assertEqual(len(evidence["sources"]), 1)
        self.assertEqual(len(evidence["facts"]), 1)
        self.assertIn("직접 원문 2개 미만", evidence["quality_warnings"])

    def test_daily_post_exists_recognizes_legacy_news_and_new_marker(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory):
            self.assertFalse(bot.daily_post_exists(now=self.now))
            path = os.path.join(directory, "2026-07-26-daily-test.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("---\nautomation: daily_ai_news\n---\n")
            self.assertTrue(bot.daily_post_exists(now=self.now))

    @mock.patch.object(bot, "generate_content_with_fallback", return_value=None)
    def test_relaxed_writer_creates_deterministic_post_when_models_fail(self, _generate):
        source = "https://example.com/news/new-model"
        candidate = {
            "topic_name": "Example AI",
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
            "source_url": source,
            "entities": ["Example AI"],
        }
        evidence = {
            "published_at": "2026-07-25",
            "sources": [{
                "url": source,
                "title": "Official announcement",
                "publisher": "Example",
                "published_at": "2026-07-25",
                "tier": "official",
            }],
            "facts": [{
                "text": "Example released a new model.",
                "source_urls": [source],
            }],
            "unknowns": ["Pricing is not published."],
            "quality_warnings": ["single source"],
        }
        post = bot.generate_blog_post(
            mock.Mock(),
            candidate,
            evidence,
            strict=False,
        )
        self.assertTrue(post["title_korean"])
        self.assertEqual(len(post["faq"]), 3)
        self.assertTrue(post["content"].startswith("```mermaid"))
        self.assertEqual(post["content"].count("```mermaid"), 3)
        self.assertTrue(all(
            item["ok"]
            for item in bot._validate_mermaid_codes(
                bot._fenced_blocks(post["content"], "mermaid")
            )
        ))
        for heading in bot.NEWS_HEADINGS:
            self.assertIn(heading, post["content"])

    def test_first_valid_mermaid_is_promoted_to_article_start(self):
        content = """
첫 문단입니다.

## 무슨 일이 벌어진 걸까?

설명입니다.

```mermaid
flowchart LR
  A["사건"] --> B["영향"]
```

## 왜 지금 다들 이 이야기를 할까?

추가 설명입니다.
""".strip()
        promoted = bot._promote_first_mermaid(content)
        self.assertTrue(promoted.startswith("```mermaid"))
        self.assertEqual(promoted.count("```mermaid"), 1)
        self.assertLess(promoted.index("```mermaid"), promoted.index("첫 문단입니다."))

    def test_markdown_normalizer_restores_news_headings_and_removes_images(self):
        raw = (
            "도입 ![가짜](https://example.com/fake.png) "
            "## 무슨 일이 벌어진 걸까? 사실 "
            "## 왜 지금 다들 이 이야기를 할까? 이유 "
            "## 그래서 우리에게 뭐가 달라질까? 영향 "
            "## 직접 써보거나 지켜볼 포인트 확인 "
            "## 아직은 선을 그어야 할 부분 한계"
        )
        fixed = bot._normalize_news_markdown(raw)
        self.assertNotIn("![", fixed)
        for heading in bot.NEWS_HEADINGS:
            self.assertIn(f"\n{heading}\n", fixed)

    def test_insert_source_images_uses_verified_credit(self):
        content = "\n\n".join([
            "도입",
            *[f"{heading}\n\n본문" for heading in bot.NEWS_HEADINGS],
        ])
        image = {
            "path": "https://cdn.example.com/official.jpg",
            "alt": "공식 제품 화면",
            "caption": "공식 발표 이미지입니다.",
            "credit": "Example",
            "source_url": "https://example.com/news/model",
        }
        output = bot.insert_source_images(content, [image])
        self.assertIn('<figure class="news-source-image">', output)
        self.assertIn("출처: Example", output)
        self.assertLess(
            output.index('<figure class="news-source-image">'),
            output.index("## 왜 지금 다들 이 이야기를 할까?"),
        )

    def test_source_links_become_numbered_citations(self):
        sources = [
            {
                "url": "https://example.com/news/model",
                "publisher": "Example",
                "title": "Official model announcement",
                "published_at": "2026-07-25",
            },
            {
                "url": "https://trusted.example.net/ai/model",
                "publisher": "Trusted Tech",
                "title": "Independent coverage",
                "published_at": "2026-07-25",
            },
        ]
        content = (
            "공식 가격이 공개됐습니다"
            "[Example](https://example.com/news/model?utm_source=blog). "
            "독립 보도도 이를 확인했습니다"
            "[Trusted Tech](https://trusted.example.net/ai/model)."
        )
        compact = bot.compact_source_citations(content, sources)
        self.assertIn('href="#source-1"', compact)
        self.assertIn('href="#source-2"', compact)
        self.assertNotIn("[Example](", compact)
        source_list = bot.source_list_html(sources)
        self.assertIn('id="source-1"', source_list)
        self.assertIn('id="source-2"', source_list)

    def test_mermaid_validator_accepts_valid_and_rejects_invalid_syntax(self):
        results = bot._validate_mermaid_codes([
            'flowchart LR\n  A["공식 발표"] --> B["사용자 확인"]',
            "this is not a mermaid diagram",
        ])
        self.assertTrue(results[0]["ok"])
        self.assertFalse(results[1]["ok"])

    def test_chartjs_requires_every_data_value_to_exist_in_verified_facts(self):
        evidence = {
            "facts": [
                {"text": "입력 가격은 5달러이고 비교 모델은 10달러입니다."},
                {"text": "출력 가격은 각각 25달러와 50달러입니다."},
            ],
        }
        grounded = json.dumps({
            "type": "bar",
            "data": {
                "labels": ["Opus 5", "Fable 5"],
                "datasets": [
                    {"label": "입력", "data": [5, 10]},
                    {"label": "출력", "data": [25, 50]},
                ],
            },
            "options": {
                "plugins": {
                    "title": {"display": True, "text": "토큰 가격 비교"}
                }
            },
        })
        invented = json.dumps({
            "type": "bar",
            "data": {
                "labels": ["Opus 5", "Fable 5"],
                "datasets": [{"label": "임의 점수", "data": [87, 99]}],
            },
            "options": {
                "plugins": {
                    "title": {"display": True, "text": "임의 점수"}
                }
            },
        })
        self.assertEqual(bot._validate_chartjs_code(grounded, evidence), (True, ""))
        valid, error = bot._validate_chartjs_code(invented, evidence)
        self.assertFalse(valid)
        self.assertIn("facts에 없는 수치", error)
        untitled = json.dumps({
            "type": "bar",
            "data": {
                "labels": ["Opus 5", "Fable 5"],
                "datasets": [{"label": "입력", "data": [5, 10]}],
            },
            "options": [],
        })
        valid, error = bot._validate_chartjs_code(untitled, evidence)
        self.assertFalse(valid)
        self.assertIn("제목", error)

    def test_visual_sanitizer_keeps_mermaid_and_drops_ungrounded_chart(self):
        content = """
```mermaid
flowchart LR
  A["발표"] --> B["확인"]
```

```chartjs
{"type":"bar","data":{"labels":["A","B"],"datasets":[{"label":"임의 점수","data":[87,99]}]},"options":{"plugins":{"title":{"display":true,"text":"임의 점수"}}}}
```
""".strip()
        with mock.patch.object(
            bot,
            "_validate_mermaid_codes",
            return_value=[{"ok": True, "error": ""}],
        ):
            sanitized, errors = bot._sanitize_news_visuals(
                content,
                {"facts": [{"text": "가격은 5달러와 10달러입니다."}]},
            )
        self.assertEqual(errors, [])
        self.assertIn("```mermaid", sanitized)
        self.assertNotIn("```chartjs", sanitized)

    def test_visual_sanitizer_drops_unsafe_mermaid_but_keeps_valid_one(self):
        content = """
```mermaid
flowchart LR
  A["공식 발표"] --> B["도입 검토"]
```

```mermaid
flowchart LR
  A["임의 점수 999"] --> B["과장"]
```
""".strip()
        with mock.patch.object(
            bot,
            "_validate_mermaid_codes",
            return_value=[
                {"ok": True, "error": ""},
                {"ok": True, "error": ""},
            ],
        ):
            sanitized, errors = bot._sanitize_news_visuals(
                content,
                {"facts": [{"text": "공식 가격은 5달러입니다."}]},
            )
        self.assertEqual(errors, [])
        self.assertEqual(sanitized.count("```mermaid"), 1)
        self.assertNotIn("999", sanitized)

    def test_save_post_keeps_existing_layout_and_writes_news_metadata(self):
        mermaid = (
            '```mermaid\n'
            'flowchart LR\n'
            '  A["공식 발표"] --> B["도입 검토"]\n'
            '```'
        )
        chart = (
            '```chartjs\n'
            '{"type":"bar","data":{"labels":["이전","현재"],'
            '"datasets":[{"label":"검증 가격","data":[10,5]}]},'
            '"options":{"plugins":{"title":{"display":true,'
            '"text":"가격 비교"}}}}\n'
            '```'
        )
        post = {
            "title_korean": "Example AI 새 모델, 실제로 달라진 세 가지",
            "title_english": "Example AI New Model Changes Three Things",
            "description": "Example AI가 공개한 새 모델의 실제 변화와 제공 범위, 도입 전에 확인할 제한 조건을 직접 원문을 바탕으로 정리합니다.",
            "summary": "Example AI가 새 모델을 공개했습니다. 실제 도입 전에는 제공 범위와 제한 조건을 확인해야 합니다.",
            "content": "\n\n".join([
                (
                    "첫 문단입니다"
                    "[Example](https://example.com/news/new-model)."
                ),
                f"{bot.NEWS_HEADINGS[0]}\n\n검증된 본문입니다.\n\n{chart}",
                f"{bot.NEWS_HEADINGS[1]}\n\n검증된 본문입니다.\n\n{mermaid}",
                *[
                    f"{heading}\n\n검증된 본문입니다."
                    for heading in bot.NEWS_HEADINGS[2:]
                ],
            ]),
            "tags": ["AI 뉴스", "Example AI", "생성형 AI", "AI 모델", "AI 트렌드"],
            "entities": ["Example AI", "Example Model"],
            "faq": [
                {"question": f"질문 {index}?", "answer": f"검증된 답변 {index}입니다."}
                for index in range(1, 4)
            ],
        }
        candidate = {
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
        }
        evidence = {
            "published_at": "2026-07-25",
            "sources": [
                {
                    "url": "https://example.com/news/new-model",
                    "title": "Official announcement",
                    "publisher": "Example",
                    "published_at": "2026-07-25",
                    "tier": "official",
                },
                {
                    "url": "https://trusted.example.net/ai/new-model",
                    "title": "Independent report",
                    "publisher": "Trusted Tech",
                    "published_at": "2026-07-25",
                    "tier": "trusted",
                },
            ],
            "facts": [
                {"text": "검증 가격은 10달러에서 5달러로 바뀌었습니다."},
                *[{"text": f"Fact {index}"} for index in range(1, 4)],
            ],
        }
        images = [
            {
                "path": "https://cdn.example.com/hero.jpg",
                "alt": "공식 이미지",
                "caption": "공식 발표 이미지입니다.",
                "credit": "Example",
                "source_url": "https://example.com/news/new-model",
            },
            {
                "path": "https://cdn.example.net/analysis.jpg",
                "alt": "보도 이미지",
                "caption": "보도와 함께 공개된 이미지입니다.",
                "credit": "Trusted Tech",
                "source_url": "https://trusted.example.net/ai/new-model",
            },
        ]
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "collect_source_images", return_value=images):
            path = bot.save_post(post, candidate, evidence, now=self.now)
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
        front_matter = yaml.safe_load(raw.split("---", 2)[1])
        self.assertEqual(front_matter["layout"], "post")
        self.assertEqual(front_matter["article_type"], "NewsArticle")
        self.assertEqual(front_matter["seo"]["type"], "NewsArticle")
        self.assertNotIn("author", front_matter)
        self.assertEqual(front_matter["image"]["creditText"], "Example")
        self.assertNotIn("source_url", front_matter["image"])
        self.assertTrue(front_matter["mermaid"])
        self.assertTrue(front_matter["chart"])
        self.assertEqual(
            front_matter["news_source_url"],
            "https://example.com/news/new-model",
        )
        self.assertNotIn("github_url", front_matter)
        self.assertNotIn("project", front_matter)
        self.assertNotIn("tags", front_matter)
        self.assertIn('<figure class="news-source-image">', raw)
        self.assertIn('href="#source-1"', raw)
        self.assertIn('id="source-1"', raw)
        self.assertNotIn("[Example](", raw)
        self.assertIn("## 직접 확인한 원문", raw)


if __name__ == "__main__":
    unittest.main()
