import datetime
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import yaml

from automation import daily_trend_bot as news_bot
from automation import guide_bot


class GuideDraftRepairTests(unittest.TestCase):
    def setUp(self):
        self.topic = {
            "id": "prompt-guide",
            "primary": "챗gpt 프롬프트 만들기",
            "format": "프롬프트와 템플릿",
            "keywords": ["챗gpt 프롬프트 만들기", "챗gpt 프롬프트 예시"],
            "tier": "T1",
        }
        self.evidence = {
            "facts": [{
                "text": "공식 문서는 명확하고 구체적인 지시를 권장합니다.",
                "source_name": "Example 공식 문서",
                "source_url": "https://example.com/docs/prompting",
            }],
            "unknowns": [],
            "reader_questions": [],
            "content_gaps": [],
            "test_requirements": [],
            "volatile": False,
        }

    @staticmethod
    def post(*, description=None, content=None):
        paragraph = (
            "프롬프트를 만들 때는 원하는 결과와 입력 자료, 지켜야 할 조건을 "
            "서로 나누어 적습니다. 공식 문서에서 확인한 범위 안에서 각 항목의 "
            "역할을 설명하고, 결과가 어긋날 때 어느 지시부터 고칠지도 함께 "
            "확인합니다. 같은 결론을 반복하지 않고 실제 작성 순서를 따라갑니다. "
        )
        if content is None:
            content = (
                "질문에 바로 답하는 도입입니다. 어떤 순서로 지시를 적을지 먼저 "
                "정하면 불필요한 시행착오를 줄일 수 있습니다.\n\n"
                "## 작성 순서\n\n" + paragraph * 15
                + "\n\n## 실패 조건\n\n" + paragraph * 15
                + "\n\n## 적용 전 확인\n\n" + paragraph * 15
            )
        return {
            "title_korean": "챗GPT 프롬프트 만들기와 수정 순서",
            "title_english": "How to Build and Revise ChatGPT Prompts",
            "description": description or (
                "챗GPT 프롬프트에 목표, 입력 자료와 제한 조건을 나누어 적고 "
                "원하는 답이 나오지 않을 때 수정할 순서를 공식 지침 범위에서 정리합니다."
            ),
            "summary": "프롬프트 구성 요소와 결과가 어긋날 때 수정할 순서를 설명합니다.",
            "content": content,
            "faq": [{"question": "무엇부터 적나요?", "answer": "목표부터 적습니다."}],
        }

    def _write(self, responses):
        with mock.patch.object(
            guide_bot.base,
            "generate_content_with_fallback",
            side_effect=[json.dumps(value, ensure_ascii=False) for value in responses],
        ) as generate, mock.patch.object(
            guide_bot,
            "load_prompt",
            return_value="가이드 작성 규칙",
        ):
            result = guide_bot.write_post(
                mock.Mock(), self.topic, self.evidence, "2026-08-30"
            )
        return result, generate

    def test_near_boundary_description_is_repaired_without_full_retry(self):
        result, generate = self._write([self.post(description="가" * 79)])

        self.assertEqual(generate.call_count, 1)
        self.assertGreaterEqual(
            len(result["description"]), guide_bot.DESCRIPTION_MIN_CHARS
        )
        self.assertLessEqual(
            len(result["description"]), guide_bot.DESCRIPTION_MAX_CHARS
        )

    def test_code_padded_short_draft_reuses_evidence_and_repairs_only_the_post(self):
        short_content = (
            "검색 질문에 답하는 설명입니다. " * 75
            + "\n\n## 템플릿\n\n```text\n"
            + ("분량으로 세면 안 되는 프롬프트 예시 " * 300)
            + "\n```\n\n## 주의점\n\n짧은 설명입니다.\n\n"
            + "## 확인 순서\n\n짧은 설명입니다."
        )
        first = self.post(content=short_content)
        second = self.post()

        result, generate = self._write([first, second])

        self.assertEqual(result["title_korean"], second["title_korean"])
        self.assertEqual(generate.call_count, 2)
        repair_prompt = generate.call_args_list[1].args[1]
        self.assertIn("실제 설명문이 너무 짧음", repair_prompt)
        self.assertIn("코드 예시와 마크다운 제외", repair_prompt)
        self.assertIn("분량으로 세면 안 되는 프롬프트 예시", repair_prompt)

    def test_exhausted_repairs_raise_before_any_save_side_effect(self):
        short = self.post(content="짧은 설명입니다.\n\n## 하나\n\n내용입니다.")
        with mock.patch.object(
            guide_bot.base,
            "generate_content_with_fallback",
            side_effect=[json.dumps(short, ensure_ascii=False)] * 3,
        ) as generate, mock.patch.object(
            guide_bot,
            "load_prompt",
            return_value="가이드 작성 규칙",
        ):
            with self.assertRaisesRegex(ValueError, "보정 횟수 소진"):
                guide_bot.write_post(
                    mock.Mock(), self.topic, self.evidence, "2026-08-30"
                )
        self.assertEqual(generate.call_count, guide_bot.WRITE_POST_ATTEMPTS)

        now = datetime.datetime(
            2026,
            8,
            30,
            15,
            0,
            tzinfo=datetime.timezone(datetime.timedelta(hours=9)),
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            guide_bot, "POSTS_DIR", directory
        ), mock.patch.object(guide_bot, "generate_card") as generate_card:
            with self.assertRaisesRegex(ValueError, "실제 설명문이 너무 짧음"):
                guide_bot.save(self.topic, short, self.evidence, now)
            generate_card.assert_not_called()
            self.assertEqual(os.listdir(directory), [])

    def test_mismatched_fence_cannot_pad_visible_prose(self):
        post = self.post(content=(
            "짧은 도입입니다.\n\n```text\n"
            + ("설명으로 세면 안 되는 코드 " * 1_000)
            + "\n~~~"
        ))

        errors = guide_bot._generated_post_errors(post)

        self.assertTrue(any("실제 설명문이 너무 짧음" in value for value in errors))
        self.assertIn("닫히지 않은 코드 펜스가 있음", errors)
        self.assertLess(guide_bot._visible_prose_length(post["content"]), 100)

    def test_save_validates_normalized_metadata_and_h1_free_body(self):
        post = self.post(description=("가" * 79) + "🙂")
        now = datetime.datetime(
            2026,
            8,
            30,
            15,
            0,
            tzinfo=datetime.timezone(datetime.timedelta(hours=9)),
        )
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            guide_bot, "POSTS_DIR", directory
        ), mock.patch.object(
            guide_bot, "insert_glossary_box", side_effect=lambda value: value
        ), mock.patch.object(
            guide_bot, "tags_for", return_value=["AI", "ChatGPT"]
        ), mock.patch.object(
            guide_bot, "generate_card", return_value="/assets/card.jpg"
        ):
            filename = guide_bot.save(self.topic, post, self.evidence, now)
            with open(os.path.join(directory, filename), encoding="utf-8") as handle:
                front_matter = yaml.safe_load(handle.read().split("---", 2)[1])

        self.assertNotIn("🙂", front_matter["description"])
        self.assertGreaterEqual(
            len(front_matter["description"]), guide_bot.DESCRIPTION_MIN_CHARS
        )

        padded_h1 = self.post(content=(
            "# " + ("본문이 아닌 긴 제목 " * 500)
            + "\n\n## 첫째\n\n실제 설명은 짧습니다."
        ))
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            guide_bot, "POSTS_DIR", directory
        ), mock.patch.object(guide_bot, "generate_card") as generate_card:
            with self.assertRaisesRegex(ValueError, "실제 설명문이 너무 짧음"):
                guide_bot.save(self.topic, padded_h1, self.evidence, now)
            generate_card.assert_not_called()
            self.assertEqual(os.listdir(directory), [])


class GeminiAndNewsFallbackTests(unittest.TestCase):
    def test_shared_generation_explicitly_disables_unused_afc(self):
        response = SimpleNamespace(text="ok")
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=mock.Mock(return_value=response))
        )

        self.assertEqual(
            news_bot.generate_content_with_fallback(client, "hello"),
            "ok",
        )
        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertTrue(config.automatic_function_calling.disable)

    def test_preflight_also_disables_unused_afc(self):
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=mock.Mock(return_value=None))
        )

        news_bot.preflight_check(client)

        config = client.models.generate_content.call_args.kwargs["config"]
        self.assertTrue(config.automatic_function_calling.disable)

    def test_daily_writer_falls_back_after_strict_draft_failure(self):
        candidate = {
            "headline": "Example releases a new AI model",
            "source_url": "https://example.com/news/model",
        }
        evidence = {
            "published_at": "2026-08-30",
            "sources": [{
                "url": candidate["source_url"],
                "publisher": "Example",
                "tier": "official",
                "reachable": True,
            }],
            "facts": [{
                "text": "Example released a model.",
                "source_urls": [candidate["source_url"]],
            }],
            "unknowns": [],
            "quality_warnings": [],
        }
        relaxed_post = {"title_korean": "검증 근거 기반 완화 원고"}

        def generate(_client, _candidate, _evidence, *, strict=True):
            return None if strict else relaxed_post

        with mock.patch.object(
            news_bot, "verify_news_candidate", return_value=evidence
        ), mock.patch.object(
            news_bot, "ensure_korean_evidence"
        ), mock.patch.object(
            news_bot, "check_duplication", return_value=False
        ), mock.patch.object(
            news_bot, "generate_blog_post", side_effect=generate
        ) as generate_post, mock.patch.object(
            news_bot, "save_post", return_value="/tmp/daily-post.md"
        ) as save_post:
            published = news_bot._publish_from_candidates(
                mock.Mock(), [candidate], history=[]
            )

        self.assertEqual(published, "/tmp/daily-post.md")
        self.assertEqual(generate_post.call_count, 2)
        self.assertNotIn("strict", generate_post.call_args_list[0].kwargs)
        self.assertFalse(generate_post.call_args_list[1].kwargs["strict"])
        save_post.assert_called_once_with(relaxed_post, candidate, evidence)

    def test_daily_fallback_rejects_unreachable_or_unlinked_sources(self):
        candidate = {
            "headline": "Unreachable AI announcement",
            "source_url": "https://example.com/missing",
        }
        evidence = {
            "published_at": "2026-08-30",
            "sources": [{
                "url": candidate["source_url"],
                "publisher": "Example",
                "tier": "official",
                "reachable": False,
            }],
            "facts": [{
                "text": "A discovery draft claimed a release.",
                "source_urls": [candidate["source_url"]],
            }],
            "quality_warnings": ["HTTP로 확인된 원문 없음"],
        }

        with mock.patch.object(
            news_bot, "verify_news_candidate", return_value=evidence
        ), mock.patch.object(news_bot, "generate_blog_post") as generate_post, \
                mock.patch.object(news_bot, "save_post") as save_post:
            published = news_bot._publish_from_candidates(
                mock.Mock(), [candidate], history=[]
            )

        self.assertIsNone(published)
        generate_post.assert_not_called()
        save_post.assert_not_called()

    def test_relaxed_writer_discards_known_invalid_draft_for_grounded_fallback(self):
        url = "https://example.com/news/model"
        candidate = {
            "topic_name": "Example AI",
            "headline": "Example releases a new AI model",
            "entities": ["Example AI"],
        }
        evidence = {
            "published_at": "2026-08-30",
            "sources": [{
                "url": url,
                "publisher": "Example",
                "tier": "official",
                "reachable": True,
            }],
            "facts": [{
                "text": "Example released a model.",
                "text_ko": "Example이 새 모델을 공개했습니다.",
                "source_urls": [url],
            }],
            "unknowns": ["Pricing is unknown."],
            "unknowns_ko": ["가격은 공개되지 않았습니다."],
            "quality_warnings": [],
        }
        invalid = {
            "title_korean": "Example 모델",
            "title_english": "Example Model",
            "description": "짧음",
            "summary": "요약입니다.",
            "content": "\n\n".join(
                f"## 섹션 {index}\n\n짧은 글입니다."
                for index in range(1, 5)
            ) + "\n\n```python\nprint('unsafe')\n```",
            "tags": ["AI"],
            "entities": ["Example AI"],
            "faq": [],
        }

        result = news_bot._relax_post_data(invalid, candidate, evidence)

        self.assertIsNotNone(result)
        self.assertNotIn("```python", result["content"])
        self.assertTrue(evidence["quality_warnings"])
        self.assertEqual(
            news_bot._post_data_errors(result, evidence),
            ["본문이 너무 짧음"],
        )


if __name__ == "__main__":
    unittest.main()
