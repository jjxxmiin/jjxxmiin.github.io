import datetime
import json
import os
import re
import tempfile
import unittest
from unittest import mock

import yaml

import tag_taxonomy

import daily_trend_bot as bot


KST = datetime.timezone(datetime.timedelta(hours=9))


class DailyTrendNewsBotTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.datetime(2026, 7, 26, 9, 0, tzinfo=KST)

    def _valid_evidence(self):
        return {
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

    def _valid_post(self):
        diagrams = [
            (
                "```mermaid\nflowchart LR\n"
                f'  A["Example 공식 발표"] --> B["검증 조건 {index}"]\n```'
            )
            for index in range(1, 4)
        ]
        paragraph = (
            "Example AI의 공식 원문에서 확인한 내용과 아직 공개되지 않은 조건을 "
            "나눠 보면 도입 판단이 쉬워집니다. 현재 작업을 바로 바꾸기보다 작은 예제에서 "
            "결과 품질, 소요 시간, 요금과 데이터 처리 조건을 같은 기준으로 비교해야 합니다. "
        ) * 7
        intro = (
            "Example AI가 새 모델을 공개했지만, 지금 바로 교체할지는 제공 범위와 "
            "미공개 조건을 나눠 확인한 뒤 결정해야 합니다. 이 글은 확인된 변화와 판단 기준을 먼저 정리합니다."
        )
        chart = (
            '```chartjs\n{"type":"bar","data":{"labels":["이전","현재"],'
            '"datasets":[{"label":"검증 가격","data":[10,5]}]},'
            '"options":{"plugins":{"title":{"display":true,'
            '"text":"가격 비교"}}}}\n```'
        )
        sections = []
        for index, heading in enumerate(bot.NEWS_HEADINGS):
            extras = []
            if index == 0:
                extras.append(chart)
            if index in (1, 2):
                extras.append(diagrams[index])
            sections.append("\n\n".join([heading, paragraph, *extras]))
        content = "\n\n".join([
            diagrams[0],
            intro + "[Example](https://example.com/news/new-model).",
            *sections,
        ])
        return {
            "title_korean": "Example AI 새 모델, 실제로 달라진 세 가지",
            "title_english": "Example AI New Model Changes Three Things",
            "description": (
                "Example AI가 공개한 새 모델의 기능과 제공 범위를 공식 발표와 "
                "독립 보도로 확인하고, 도입 전 비교할 기준과 아직 검증되지 않은 한계를 함께 정리합니다."
            ),
            "summary": (
                "Example AI가 새 모델을 공개했습니다. 실제 도입 전에는 제공 범위와 "
                "제한 조건을 확인해야 합니다."
            ),
            "content": content,
            "tags": ["AI 뉴스", "Example AI", "생성형 AI", "AI 모델", "AI 트렌드"],
            "entities": ["Example AI", "Example Model"],
            "faq": [
                {"question": f"질문 {index}?", "answer": f"검증된 답변 {index}입니다."}
                for index in range(1, 4)
            ],
        }

    def test_pipeline_uses_only_gemini_3_6_flash_with_request_timeout(self):
        self.assertEqual(bot.FALLBACK_MODELS, ["gemini-3.6-flash"])
        with mock.patch.object(bot.genai, "Client") as client, \
                mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            bot.get_gemini_client()
        kwargs = client.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "test-key")
        self.assertEqual(
            kwargs["http_options"].timeout,
            bot.GEMINI_HTTP_TIMEOUT_MS,
        )
        self.assertGreaterEqual(bot.MAX_CANDIDATES_PER_SEARCH, 1)
        self.assertLessEqual(bot.MAX_CANDIDATES_PER_SEARCH, 8)

    def test_each_search_pass_has_a_bounded_candidate_budget(self):
        candidates = [{"trend_score": score} for score in range(10, 0, -1)]
        with mock.patch.object(bot, "MAX_CANDIDATES_PER_SEARCH", 3):
            limited = bot._limit_trending_candidates(candidates)
        self.assertEqual([item["trend_score"] for item in limited], [10, 9, 8])

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
    def test_relaxed_writer_rejects_short_fallback_when_models_fail(self, _generate):
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
            "summary_flow": [
                "Example 새 모델 공개", "7월 25일 공식 발표", "가격 미공개",
            ],
        }
        post = bot.generate_blog_post(
            mock.Mock(),
            candidate,
            evidence,
            strict=False,
        )
        self.assertIsNone(post)
        fallback = bot._fallback_post_data(candidate, evidence)
        errors = bot._post_data_errors(fallback, evidence)
        self.assertIn("실제 설명 본문이 너무 짧음", errors)
        self.assertIn("Mermaid 다이어그램은 3~5개 필요", errors)

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
        post = self._valid_post()
        candidate = {
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
        }
        evidence = self._valid_evidence()
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
        # 태그는 통제 어휘(tag_taxonomy)에서 결정론적으로 뽑아 넣는다.
        # 모델이 만들어낸 자유형 태그("AI 뉴스", "생성형 AI" 등)는 표기가 매번
        # 흔들려 태그 공간을 파편화시키므로 프론트매터에 그대로 쓰지 않는다.
        # Chirpy 관련글이 태그 교집합으로 동작하기 때문에 이 구분이 중요하다.
        self.assertIn("tags", front_matter)
        self.assertTrue(front_matter["tags"], "태그가 비어 있으면 관련글에서 고립된다")
        vocabulary = {name for name, _patterns, _opts in tag_taxonomy.TAXONOMY}
        self.assertTrue(
            set(front_matter["tags"]) <= vocabulary,
            f"통제 어휘 밖의 태그: {set(front_matter['tags']) - vocabulary}",
        )
        self.assertNotIn("AI 뉴스", front_matter["tags"])
        self.assertIn('<figure class="news-source-image">', raw)
        self.assertIn('href="#source-1"', raw)
        self.assertIn('id="source-1"', raw)
        self.assertNotIn("[Example](", raw)
        self.assertIn("## 직접 확인한 원문", raw)

    def test_save_post_without_source_images_generates_card_before_using_content(self):
        post = self._valid_post()
        candidate = {
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
        }
        evidence = self._valid_evidence()
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "collect_source_images", return_value=[]), \
                mock.patch.object(
                    bot,
                    "generate_card",
                    return_value="/assets/img/thumb/example-card.jpg",
                ) as generate_card:
            path = bot.save_post(post, candidate, evidence, now=self.now)
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()

        front_matter = yaml.safe_load(raw.split("---", 2)[1])
        self.assertEqual(
            front_matter["image"]["path"],
            "/assets/img/thumb/example-card.jpg",
        )
        self.assertTrue(generate_card.called)

    def test_save_post_rejects_invalid_post_before_collecting_images_or_writing(self):
        post = self._valid_post()
        post["content"] = "\n\n".join(
            ["```mermaid\nflowchart LR\n  A --> B\n```", "짧은 도입"]
            + [f"{heading}\n\n짧은 본문" for heading in bot.NEWS_HEADINGS]
        )
        candidate = {
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
        }
        evidence = self._valid_evidence()
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "collect_source_images") as collect_images:
            with self.assertRaisesRegex(ValueError, "저장 전 글 품질 검증 실패"):
                bot.save_post(post, candidate, evidence, now=self.now)
            self.assertEqual(os.listdir(directory), [])
        collect_images.assert_not_called()

    def test_save_post_revalidates_after_empty_lead_diagram_is_removed(self):
        post = self._valid_post()
        generic = (
            "```mermaid\nflowchart LR\n"
            '  A["오늘의 AI 변화"] --> B["직접 원문 확인"]\n'
            '  B --> C["사용자와 개발자 영향"]\n```'
        )
        post["content"] = re.sub(
            r"```mermaid\n.*?\n```", generic, post["content"], count=1, flags=re.S
        )
        evidence = self._valid_evidence()
        evidence["summary_flow"] = []
        candidate = {
            "headline": "Example releases a new model",
            "published_at": "2026-07-25",
        }
        self.assertEqual(bot._post_data_errors(post, evidence), [])

        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "collect_source_images") as collect_images:
            with self.assertRaises(ValueError) as raised:
                bot.save_post(post, candidate, evidence, now=self.now)
            self.assertEqual(os.listdir(directory), [])
        collect_images.assert_not_called()
        message = str(raised.exception)
        self.assertIn("최종 변환 후 글 품질 검증 실패", message)
        self.assertIn("글 첫 부분에 전체 흐름 Mermaid가 없음", message)
        self.assertIn("Mermaid 다이어그램은 3~5개 필요", message)

    def test_visible_prose_keeps_plain_less_than_comparison(self):
        text = "이 모델의 지연은 < 5 ms라는 조건을 비교합니다.\n\n다음 판단을 이어갑니다."
        self.assertIn("< 5 ms", bot._visible_prose(text))


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# 요약 흐름도: 어느 글에 붙여도 말이 되는 그림은 넣지 않는다.
# ---------------------------------------------------------------------------
EVIDENCE_FOR_FLOW = {
    "sources": [{"url": "https://openrouter.ai/x", "publisher": "OpenRouter",
                 "title": "t", "published_at": "2026-08-20", "tier": "official",
                 "reachable": True}],
    "facts": [{"text": "Ox Alpha offers a 1,048,576-token context window.",
               "text_ko": "Ox Alpha 는 1,048,576 토큰을 지원합니다.",
               "source_urls": ["https://openrouter.ai/x"]}],
    "unknowns": [],
    "unknowns_ko": [],
    "summary_flow": ["8월 20일 OpenRouter 공개", "컨텍스트 100만 토큰",
                     "프리뷰 무료", "개발사 미확인"],
}

EMPTY_DIAGRAM = """flowchart LR
    A["오늘의 AI 변화"] --> B["직접 원문 확인"]
    B --> C["사용자와 개발자 영향"]"""

REAL_DIAGRAM = """flowchart LR
    A["OpenRouter 무료 공개"] --> B["컨텍스트 100만 토큰"]"""


def test_빈_말_다이어그램을_찾아낸다():
    assert bot.diagram_is_empty_talk(EMPTY_DIAGRAM, EVIDENCE_FOR_FLOW)


def test_숫자가_있으면_빈_말이_아니다():
    assert not bot.diagram_is_empty_talk(REAL_DIAGRAM, EVIDENCE_FOR_FLOW)


def test_고유명사가_있으면_빈_말이_아니다():
    diagram = 'flowchart LR\n    A["OpenRouter 공개"] --> B["무료 제공"]'
    assert not bot.diagram_is_empty_talk(diagram, EVIDENCE_FOR_FLOW)


def test_요약_흐름도는_검증된_문구로_만든다():
    code = bot.build_flow_diagram(EVIDENCE_FOR_FLOW)
    assert "컨텍스트 100만 토큰" in code
    assert code.startswith("```mermaid")
    assert code.rstrip().endswith("```")


def test_빈_말_문구는_흐름도에서_걸러진다():
    evidence = dict(EVIDENCE_FOR_FLOW, summary_flow=["사건", "영향", "한계"])
    assert bot.build_flow_diagram(evidence) == ""


def test_라벨의_괄호와_콜론은_지운다():
    label = bot.clean_flow_label('가격(월 20달러): "정액"')
    for broken in "()[]{}:\"'":
        assert broken not in label


def test_글머리_빈_다이어그램은_사실_기반으로_바뀐다():
    content = f"```mermaid\n{EMPTY_DIAGRAM}\n```\n\n## 무슨 일이\n\n본문입니다.\n"
    out = bot.replace_empty_lead_diagram(content, EVIDENCE_FOR_FLOW)
    assert "오늘의 AI 변화" not in out
    assert "컨텍스트 100만 토큰" in out
    assert out.count("## 무슨 일이") == 1


def test_쓸_만한_그림은_건드리지_않는다():
    content = f"```mermaid\n{REAL_DIAGRAM}\n```\n\n## 무슨 일이\n\n본문입니다.\n"
    assert bot.replace_empty_lead_diagram(content, EVIDENCE_FOR_FLOW) == content


def test_대체할_재료가_없으면_빈_그림을_지운다():
    evidence = dict(EVIDENCE_FOR_FLOW, summary_flow=[])
    content = f"```mermaid\n{EMPTY_DIAGRAM}\n```\n\n## 무슨 일이\n\n본문입니다.\n"
    out = bot.replace_empty_lead_diagram(content, evidence)
    assert "mermaid" not in out
    assert out.startswith("## 무슨 일이")


def test_한국어_고유_내용이_있으면_지우지_않는다():
    # 숫자도 영문도 없지만 사실에 나온 말을 담은 그림은 이 글의 그림이다.
    evidence = {
        "sources": [{"publisher": "OpenRouter"}],
        "facts": [{"text": "", "text_ko": "무료 프리뷰 기간에는 요금이 없습니다."}],
    }
    diagram = 'flowchart LR\n    A["무료 프리뷰"] --> B["요금 없음"]'
    assert not bot.diagram_is_empty_talk(diagram, evidence)


def test_상투적인_문구가_없으면_애매해도_놔둔다():
    evidence = {"sources": [{"publisher": "OpenRouter"}], "facts": []}
    diagram = 'flowchart LR\n    A["어떤 흐름"] --> B["다른 흐름"]'
    assert not bot.diagram_is_empty_talk(diagram, evidence)
