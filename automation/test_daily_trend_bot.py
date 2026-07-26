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

    def test_save_post_keeps_existing_layout_and_writes_news_metadata(self):
        post = {
            "title_korean": "Example AI 새 모델, 실제로 달라진 세 가지",
            "title_english": "Example AI New Model Changes Three Things",
            "description": "Example AI가 공개한 새 모델의 실제 변화와 제공 범위, 도입 전에 확인할 제한 조건을 직접 원문을 바탕으로 정리합니다.",
            "summary": "Example AI가 새 모델을 공개했습니다. 실제 도입 전에는 제공 범위와 제한 조건을 확인해야 합니다.",
            "content": "\n\n".join([
                "첫 문단입니다.",
                *[f"{heading}\n\n검증된 본문입니다." for heading in bot.NEWS_HEADINGS],
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
            "facts": [{"text": f"Fact {index}"} for index in range(4)],
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
        self.assertEqual(
            front_matter["news_source_url"],
            "https://example.com/news/new-model",
        )
        self.assertNotIn("github_url", front_matter)
        self.assertNotIn("project", front_matter)
        self.assertIn('<figure class="news-source-image">', raw)
        self.assertIn("## 직접 확인한 원문", raw)


if __name__ == "__main__":
    unittest.main()
