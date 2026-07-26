import datetime as dt
import os
import tempfile
import unittest
from unittest import mock
from zoneinfo import ZoneInfo

import yaml

import daily_ai_news_bot as bot


class DailyAiNewsBotTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 7, 26, 9, 0, tzinfo=ZoneInfo("Asia/Seoul"))

    def test_canonical_url_removes_tracking(self):
        value = bot.canonical_url(
            "HTTPS://Example.COM/news/ai/?utm_source=x&keep=1&fbclid=abc#part"
        )
        self.assertEqual(value, "https://example.com/news/ai?keep=1")

    def test_direct_source_rejects_search_landing_and_assets(self):
        self.assertEqual(
            bot.direct_source_rejection_reason("https://news.google.com/search?q=ai"),
            "검색 결과 URL",
        )
        self.assertEqual(
            bot.direct_source_rejection_reason("https://example.com/news"),
            "홈페이지 또는 섹션 URL",
        )
        self.assertEqual(
            bot.direct_source_rejection_reason("https://cdn.example.com/hero.png"),
            "기사/발표 원문이 아닌 파일 URL",
        )
        self.assertIsNone(
            bot.direct_source_rejection_reason("https://example.com/2026/07/new-ai-model")
        )

    def test_recent_publication_enforces_window(self):
        self.assertTrue(bot.recent_publication("2026-07-25", now=self.now, max_days=7))
        self.assertFalse(bot.recent_publication("2026-07-10", now=self.now, max_days=7))
        self.assertFalse(bot.recent_publication("unknown", now=self.now, max_days=7))

    def test_duplicate_story_by_source_url(self):
        candidate = {
            "headline": "새 AI 기능 공개",
            "topic_name": "Example AI",
            "source_url": "https://example.com/story?utm_source=x",
            "entities": ["Example", "Example AI"],
        }
        history = [{
            "title": "Example AI 새 기능",
            "summary": "",
            "sourceUrl": "https://example.com/story",
            "entities": [],
        }]
        self.assertTrue(bot.is_duplicate_story(candidate, history))

    @mock.patch.object(bot, "probe_source")
    def test_evidence_normalization_and_validation(self, probe):
        probe.side_effect = lambda url: {
            "http_status": 200,
            "http_verified": True,
            "final_url": bot.canonical_url(url),
        }
        raw = {
            "thesis": "공식 발표로 새 기능이 제공됐다.",
            "sources": [
                {
                    "id": "old1",
                    "url": "https://official.example.com/announcements/new-ai",
                    "title": "Official announcement",
                    "publisher": "Example",
                    "published_at": "2026-07-25",
                    "tier": "official",
                    "reachable": True,
                },
                {
                    "id": "old2",
                    "url": "https://trusted.example.net/tech/example-ai-launch",
                    "title": "Launch coverage",
                    "publisher": "Trusted Tech",
                    "published_at": "2026-07-25",
                    "tier": "trusted",
                    "reachable": True,
                },
            ],
            "claims": [
                {
                    "id": f"old{index}",
                    "text": f"검증된 주장 {index}",
                    "type": "fact",
                    "evidence_ids": ["old1", "old2"],
                    "supported": True,
                    "confidence": 0.9,
                }
                for index in range(1, 4)
            ],
            "unknowns": [],
            "forbidden_claims": [],
        }
        evidence = bot.normalize_evidence(raw, now=self.now)
        self.assertEqual(bot.evidence_errors(evidence), [])
        self.assertEqual([source["id"] for source in evidence["sources"]], ["s1", "s2"])
        self.assertEqual(evidence["claims"][0]["evidence_ids"], ["s1", "s2"])

    def test_normalize_news_markdown_restores_collapsed_headings_and_fence(self):
        collapsed = (
            "Opening. ## What actually happened? Body. "
            "## How did an offline sandbox get out? Explanation. "
            "```mermaid graph TD; A-->B; ``` "
            "## Why should you care? Impact. "
            "## What should teams do now? Checks. "
            "## What do we still not know? Limits."
        )
        fixed = bot.normalize_news_markdown(collapsed)
        self.assertIn("\n## What actually happened?\n", fixed)
        self.assertIn("\n## Why should you care?\n", fixed)
        self.assertIn("```mermaid\ngraph TD; A-->B;\n```", fixed)
        self.assertEqual(bot.markdown_structure_errors(fixed), [])

    def test_normalize_korean_news_markdown_restores_headings(self):
        collapsed = (
            "도입. ## 대체 무슨 일이 있었나? 본문. "
            "## 인터넷도 막았는데 어떻게 나갔을까? 설명. "
            "## 이게 우리한테 왜 중요할까? 영향. "
            "## 지금 바로 확인할 것 확인. ## 아직 모르는 것 한계."
        )
        fixed = bot.normalize_news_markdown(
            collapsed,
            headings=bot.EXPECTED_NEWS_HEADINGS_KO,
        )
        self.assertIn("\n## 대체 무슨 일이 있었나?\n", fixed)
        self.assertIn("\n## 아직 모르는 것\n", fixed)
        self.assertEqual(bot.markdown_structure_errors(fixed), [])

    def test_source_image_meta_parser_prefers_declared_share_image(self):
        parser = bot.SourceImageMetaParser()
        parser.feed(
            '<meta property="og:image" content="/images/official-story.png">'
            '<meta property="og:image:alt" content="Official incident graphic">'
            '<meta name="twitter:image" content="https://cdn.example.com/backup.jpg">'
        )
        self.assertEqual(
            parser.image_candidates(),
            [
                "/images/official-story.png",
                "https://cdn.example.com/backup.jpg",
            ],
        )
        self.assertEqual(parser.image_alt, "Official incident graphic")

    def test_private_image_targets_are_rejected(self):
        self.assertFalse(bot._safe_remote_url("http://example.com/image.png"))
        self.assertFalse(bot._safe_remote_url("https://localhost/image.png"))
        self.assertFalse(bot._safe_remote_url("https://127.0.0.1/image.png"))
        self.assertFalse(bot._safe_remote_url("https://169.254.169.254/latest/meta-data"))
        self.assertTrue(bot._safe_remote_url("https://cdn.example.com/image.png"))

    def test_save_post_writes_news_metadata_and_visible_answers(self):
        post = {
            "title": "Example AI Launches a Verified New Feature",
            "description": "Example AI released a verified new feature. This report explains its scope, availability, practical impact, and remaining limitations.",
            "summary": "Example AI released a new feature. Readers should verify its rollout scope before adopting it.",
            "content": (
                "Opening.\n\n## What actually happened?\n\nOfficial announcement.\n\n"
                "## How did an offline sandbox get out?\n\nThe documented process.\n\n"
                "## Why should you care?\n\nAffected readers.\n\n"
                "## What should teams do now?\n\nCheck availability.\n\n"
                "## What do we still not know?\n\nKnown limits."
            ),
            "tags": ["AI news", "Example AI"],
            "entities": ["Example AI"],
            "key_takeaways": ["First takeaway.", "Second takeaway.", "Third takeaway."],
            "faq": [
                {"question": f"Question {index}?", "answer": f"Answer {index}."}
                for index in range(1, 5)
            ],
        }
        candidate = {
            "source_url": "https://official.example.com/announcements/new-ai",
            "published_at": "2026-07-25",
        }
        editorial = {"news_angle": "업무 영향", "reader_question": "무엇이 달라지나?"}
        evidence = {
            "sources": [{
                "publisher": "Example",
                "title": "Official announcement",
                "url": candidate["source_url"],
                "published_at": "2026-07-25",
            }],
            "claims": [{"supported": True}, {"supported": True}, {"supported": True}],
        }
        collected = [
            {
                "path": "/assets/img/news/example-official-source.png",
                "alt": "Official Example AI product image",
                "caption": "Image published with the official announcement.",
                "credit": "Example",
                "source_url": candidate["source_url"],
                "original_url": "https://official.example.com/images/launch.png",
                "width": 1600,
                "height": 900,
            },
            {
                "path": "/assets/img/news/example-analysis-source.jpg",
                "alt": "Example AI feature interface",
                "caption": "Image published with independent coverage.",
                "credit": "Trusted Tech",
                "source_url": "https://trusted.example.net/tech/example-ai-launch",
                "original_url": "https://trusted.example.net/images/example-ai.jpg",
                "width": 1200,
                "height": 675,
            },
        ]
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "NEWS_IMAGES_DIR", os.path.join(directory, "images")), \
                mock.patch.object(bot, "collect_source_images", return_value=collected):
            path = bot.save_post(
                post, candidate, editorial, evidence, now=self.now
            )
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
            front_matter = yaml.safe_load(raw.split("---", 2)[1])
            self.assertEqual(front_matter["article_type"], "NewsArticle")
            self.assertEqual(front_matter["lang"], "en")
            self.assertEqual(front_matter["news_source_url"], candidate["source_url"])
            self.assertEqual(front_matter["image"]["credit"], "Example")
            self.assertEqual(front_matter["image"]["width"], 1600)
            self.assertEqual(len(front_matter["article_images"]), 1)
            self.assertEqual(
                front_matter["article_images"][0]["credit"], "Trusted Tech"
            )
            self.assertNotIn("## Key takeaways", raw)
            self.assertIn("## People are asking", raw)
            self.assertIn("## Sources we checked", raw)
            self.assertEqual(raw.count('<figure class="news-visual">'), 1)
            self.assertIn("Credit: Trusted Tech", raw)
            self.assertTrue(os.path.isfile(path))

    def test_save_bilingual_posts_creates_linked_language_pair(self):
        english = {
            "title": "Example AI Launches a Verified Feature",
            "description": "A sufficiently detailed English description for the verified Example AI feature and its practical deployment scope.",
            "summary": "A verified English summary.",
            "content": (
                "Opening.\n\n## What actually happened?\n\nFact.\n\n"
                "## How did an offline sandbox get out?\n\nProcess.\n\n"
                "## Why should you care?\n\nImpact.\n\n"
                "## What should teams do now?\n\nWatch.\n\n"
                "## What do we still not know?\n\nLimits."
            ),
            "tags": ["Example AI"], "entities": ["Example AI"],
            "key_takeaways": ["One.", "Two.", "Three."],
            "faq": [
                {"question": f"Question {index}?", "answer": f"Answer {index}."}
                for index in range(1, 5)
            ],
        }
        korean = {
            **english,
            "title": "Example AI, 검증된 기능 출시",
            "description": "Example AI가 공개한 새 기능의 범위와 실제 도입 전에 확인해야 할 조건을 직접 출처를 바탕으로 자세히 설명합니다.",
            "summary": "검증된 한국어 요약입니다.",
            "content": (
                "도입.\n\n## 대체 무슨 일이 있었나?\n\n사실.\n\n"
                "## 인터넷도 막았는데 어떻게 나갔을까?\n\n과정.\n\n"
                "## 이게 우리한테 왜 중요할까?\n\n영향.\n\n"
                "## 지금 바로 확인할 것\n\n확인.\n\n"
                "## 아직 모르는 것\n\n한계."
            ),
            "key_takeaways": ["하나.", "둘.", "셋."],
            "faq": [
                {"question": f"질문 {index}?", "answer": f"답변 {index}."}
                for index in range(1, 5)
            ],
        }
        candidate = {
            "source_url": "https://official.example.com/announcements/new-ai",
            "published_at": "2026-07-25",
        }
        editorial = {"news_angle": "impact", "reader_question": "what changed?"}
        evidence = {
            "sources": [{
                "publisher": "Example",
                "title": "Official announcement",
                "url": candidate["source_url"],
                "published_at": "2026-07-25",
                "tier": "official",
            }],
            "claims": [{"supported": True}, {"supported": True}, {"supported": True}],
        }
        collected = [{
            "path": "/assets/img/news/example-source.png",
            "alt": "Example source image",
            "caption": "Image published with the source.",
            "credit": "Example",
            "source_url": candidate["source_url"],
            "original_url": "https://official.example.com/images/example.png",
            "width": 1200,
            "height": 630,
        }]
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(
                    bot, "collect_source_images", return_value=collected
                ) as collect:
            paths = bot.save_bilingual_posts(
                english, korean, candidate, editorial, evidence, now=self.now
            )
            self.assertEqual(len(paths), 2)
            collect.assert_called_once()
            front_matters = []
            for path in paths:
                with open(path, encoding="utf-8") as handle:
                    front_matters.append(yaml.safe_load(handle.read().split("---", 2)[1]))
            self.assertEqual(
                {item["lang"] for item in front_matters}, {"en", "ko-KR"}
            )
            self.assertEqual(
                {item["translation_key"] for item in front_matters},
                {"example-ai-launches-a-verified-feature"},
            )
            for item in front_matters:
                self.assertEqual(
                    item["translations"]["en"],
                    "/en/news/example-ai-launches-a-verified-feature/",
                )
                self.assertEqual(
                    item["translations"]["ko"],
                    "/ko/news/example-ai-launches-a-verified-feature/",
                )


if __name__ == "__main__":
    unittest.main()
