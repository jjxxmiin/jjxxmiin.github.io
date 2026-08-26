import datetime
import json
import os
import tempfile
import unittest
from unittest import mock

import yaml

from automation import guide_bot as bot


KST = datetime.timezone(datetime.timedelta(hours=9))


class GuideBotPublishingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.datetime(2026, 8, 26, 9, 0, tzinfo=KST)
        self.topic = {
            "id": "test-guide",
            "primary": "AI 요금제 비교",
            "tier": "A",
        }
        self.evidence = {
            "facts": [{
                "source_url": "https://example.com/pricing",
                "source_name": "Example 공식 요금 안내",
            }],
            "volatile": False,
        }

    @staticmethod
    def valid_post() -> dict:
        intro = (
            "AI 요금제를 고를 때는 월 가격만 비교하지 말고 사용량 한도와 지원 기능, "
            "해지 조건을 함께 확인해야 합니다. 이 글은 공식 안내에서 확인한 항목을 "
            "기준으로 선택 순서를 바로 적용할 수 있게 정리합니다."
        )
        paragraph = (
            "먼저 실제 사용 목적과 한 달 동안 필요한 요청 횟수를 적습니다. "
            "그다음 각 요금제가 제공하는 기능과 제한 조건을 같은 기준으로 비교합니다. "
            "표시된 가격만 보고 결정하면 필요한 기능이 빠져 다시 바꾸게 될 수 있으므로 "
            "공식 안내의 적용 범위와 변경 가능성까지 확인하는 과정이 중요합니다. "
        )
        sections = []
        for index, heading in enumerate(("선택 기준", "요금제 비교 방법", "결정 전 확인 사항"), 1):
            sections.append(f"## {heading}\n\n" + paragraph * 12 + f"단계 {index}을 기록합니다.")
        return {
            "title_korean": "AI 요금제 비교와 선택 기준 가이드",
            "title_english": "AI Pricing Plan Comparison Guide",
            "description": (
                "AI 요금제의 가격, 사용량 한도, 지원 기능과 변경 조건을 공식 안내 기준으로 "
                "비교하고 자신의 사용 목적에 맞는 플랜을 고르는 순서를 정리합니다."
            ),
            "summary": "가격과 사용량, 기능 제한을 같은 기준으로 비교하는 방법을 설명합니다.",
            "content": intro + "\n\n" + "\n\n".join(sections),
            "faq": [{
                "question": "AI 요금제는 가격만 비교하면 되나요?",
                "answer": "가격과 함께 사용량 한도, 필요한 기능, 변경 조건을 확인해야 합니다.",
            }],
        }

    def test_valid_guide_is_validated_before_save(self):
        post = self.valid_post()
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "insert_glossary_box", side_effect=lambda value: value), \
                mock.patch.object(bot, "tags_for", return_value=["AI", "생성형 AI"]), \
                mock.patch.object(
                    bot,
                    "generate_card",
                    return_value="/assets/img/thumb/ai-pricing-plan-comparison-guide.jpg",
                ):
            filename = bot.save(self.topic, post, self.evidence, self.now)
            path = os.path.join(directory, filename)
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()

        front_matter = yaml.safe_load(raw.split("---", 2)[1])
        self.assertEqual(
            front_matter["image"]["path"],
            "/assets/img/thumb/ai-pricing-plan-comparison-guide.jpg",
        )
        self.assertIn("## 자주 묻는 질문", raw)
        self.assertIn(post["faq"][0]["answer"], raw)

    def test_thumbnail_failure_raises_and_does_not_write_post(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "insert_glossary_box", side_effect=lambda value: value), \
                mock.patch.object(bot, "tags_for", return_value=["AI", "생성형 AI"]), \
                mock.patch.object(
                    bot,
                    "generate_card",
                    side_effect=RuntimeError("chromium unavailable"),
                ):
            with self.assertRaisesRegex(RuntimeError, "대표 이미지 생성 실패"):
                bot.save(self.topic, self.valid_post(), self.evidence, self.now)
            self.assertEqual(os.listdir(directory), [])

    def test_short_code_padded_guide_fails_before_thumbnail_and_writes_nothing(self):
        post = self.valid_post()
        post["content"] = (
            "가격과 한도를 함께 확인하면 자신에게 맞는 요금제를 고를 수 있습니다. "
            "공식 문서를 기준으로 조건을 비교하고 결정 전에 최신 내용을 다시 확인합니다.\n\n"
            "## 첫째\n\n짧은 설명입니다.\n\n"
            "## 둘째\n\n짧은 설명입니다.\n\n"
            "## 셋째\n\n짧은 설명입니다.\n\n"
            "```text\n" + ("분량으로 세면 안 되는 코드와 이미지 " * 500) + "\n```\n\n"
            "![길게 쓴 이미지 대체문](/assets/example.png)"
        )
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "insert_glossary_box", side_effect=lambda value: value), \
                mock.patch.object(bot, "tags_for", return_value=["AI", "생성형 AI"]), \
                mock.patch.object(bot, "generate_card") as generate_card:
            with self.assertRaisesRegex(ValueError, "실제 설명문이 너무 짧음"):
                bot.save(self.topic, post, self.evidence, self.now)
            generate_card.assert_not_called()
            self.assertEqual(os.listdir(directory), [])

    def test_non_atx_headings_and_too_many_faq_fail_before_thumbnail(self):
        post = self.valid_post()
        post["content"] = post["content"].replace("## 선택 기준", "선택 기준\n-----------")
        post["faq"] = [
            {"question": f"질문 {index}은 무엇인가요?", "answer": f"답변 {index}입니다."}
            for index in range(1, 7)
        ]
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(bot, "POSTS_DIR", directory), \
                mock.patch.object(bot, "insert_glossary_box", side_effect=lambda value: value), \
                mock.patch.object(bot, "tags_for", return_value=["AI", "생성형 AI"]), \
                mock.patch.object(bot, "generate_card") as generate_card:
            with self.assertRaises(ValueError) as raised:
                bot.save(self.topic, post, self.evidence, self.now)
            message = str(raised.exception)
            self.assertIn("ATX(#)가 아닌 제목 문법", message)
            self.assertIn("FAQ가 5개를 초과", message)
            generate_card.assert_not_called()
            self.assertEqual(os.listdir(directory), [])

    def test_visible_text_keeps_math_comparison_but_excludes_non_prose(self):
        markdown = (
            "수식 y_{<t}의 다음 설명은 사라지면 안 됩니다 > 비교 결과입니다.\n\n"
            "![세지 않을 이미지 설명](https://example.com/a_(b).png)\n\n"
            "```text\n세지 않을 코드 문장\n```\n\n"
            "<div class=\"note\">화면에 보이는 HTML 본문</div>"
        )
        visible = bot._visible_text(markdown)
        self.assertIn("다음 설명은 사라지면 안 됩니다", visible)
        self.assertIn("화면에 보이는 HTML 본문", visible)
        self.assertNotIn("세지 않을 이미지 설명", visible)
        self.assertNotIn("세지 않을 코드 문장", visible)

    def test_writer_rejects_clickbait_missing_summary_and_false_experience(self):
        post = self.valid_post()
        post["title_korean"] = "[충격] AI 요금제의 궁극의 선택"
        post["summary"] = ""
        post["content"] = "제가 직접 현업에서 검증했습니다. " + post["content"]
        topic = {
            **self.topic,
            "format": "comparison",
            "keywords": ["AI 요금제 비교"],
        }
        evidence = {
            "facts": [{
                "text": "공식 페이지에 요금 조건이 공개되어 있습니다.",
                "source_name": "Example",
                "source_url": "https://example.com/pricing",
                "source_tier": "official",
            }],
            "unknowns": [],
        }
        with mock.patch.object(
            bot.base,
            "generate_content_with_fallback",
            return_value=json.dumps(post, ensure_ascii=False),
        ), mock.patch.object(bot, "load_prompt", return_value="가이드 프롬프트"):
            with self.assertRaises(ValueError) as raised:
                bot.write_post(mock.Mock(), topic, evidence, "2026-08-26")
        message = str(raised.exception)
        self.assertIn("낚시성 또는 허위 경험 제목", message)
        self.assertIn("요약 누락", message)
        self.assertIn("근거 없는 1인칭 경험", message)

    def test_research_keeps_five_reachable_direct_facts_and_prefers_official(self):
        payload = {
            "facts": [
                {
                    "text": "공식 가격은 월 20달러입니다.",
                    "source_url": "http://OFFICIAL.example.com/docs/pricing/?utm_source=x",
                    "source_name": "Example 공식 가격표",
                    "source_tier": "primary",
                },
                *[
                    {
                        "text": f"검증된 조건 {index}입니다.",
                        "source_url": f"https://media.example.net/article/{index}",
                        "source_name": "Trusted Media",
                        "source_tier": "trusted",
                    }
                    for index in range(1, 5)
                ],
                {
                    "text": "검증된 조건 1입니다.",
                    "source_url": "https://another.example.org/report/duplicate",
                    "source_name": "Duplicate Report",
                    "source_tier": "trusted",
                },
                {
                    "text": "검색 결과는 근거가 아닙니다.",
                    "source_url": "https://www.google.com/search?q=pricing",
                    "source_name": "Google",
                    "source_tier": "trusted",
                },
                {
                    "text": "404 페이지의 주장입니다.",
                    "source_url": "https://media.example.net/article/missing",
                    "source_name": "Missing",
                    "source_tier": "trusted",
                },
            ],
            "unknowns": ["연간 할인은 확인되지 않았습니다."],
            "volatile": True,
        }

        def probe(url):
            return {
                "url": url,
                "status": 404 if url.endswith("/missing") else 200,
                "reachable": not url.endswith("/missing"),
            }

        topic = {
            **self.topic,
            "format": "comparison",
            "keywords": ["AI 요금제 비교"],
        }
        with mock.patch.object(
            bot.base,
            "generate_content_with_fallback",
            return_value=json.dumps(payload, ensure_ascii=False),
        ), mock.patch.object(bot.base, "probe_source", side_effect=probe):
            evidence = bot.research(mock.Mock(), topic, "2026-08-26")

        self.assertEqual(len(evidence["facts"]), 5)
        self.assertEqual(evidence["facts"][0]["source_tier"], "official")
        self.assertEqual(
            evidence["facts"][0]["source_url"],
            "https://official.example.com/docs/pricing",
        )
        self.assertEqual(
            len({fact["text"] for fact in evidence["facts"]}),
            len(evidence["facts"]),
        )
        self.assertTrue(evidence["volatile"])

    def test_research_fails_when_fewer_than_five_direct_facts_survive(self):
        payload = {
            "facts": [{
                "text": f"사실 {index}",
                "source_url": f"https://official.example.com/docs/{index}",
                "source_name": "Official",
                "source_tier": "official",
            } for index in range(1, 5)],
            "unknowns": [],
            "volatile": False,
        }
        topic = {
            **self.topic,
            "format": "comparison",
            "keywords": ["AI 요금제 비교"],
        }
        with mock.patch.object(
            bot.base,
            "generate_content_with_fallback",
            return_value=json.dumps(payload, ensure_ascii=False),
        ), mock.patch.object(
            bot.base,
            "probe_source",
            side_effect=lambda url: {"url": url, "status": 200, "reachable": True},
        ):
            with self.assertRaisesRegex(ValueError, "직접 근거 사실 5개 미만"):
                bot.research(mock.Mock(), topic, "2026-08-26")

    def test_publish_rolls_back_post_when_ledger_write_fails_then_retries_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            posts = os.path.join(directory, "posts")
            ledger = os.path.join(directory, "data", "written_topics.json")
            os.makedirs(posts)
            with mock.patch.object(bot, "POSTS_DIR", posts), \
                    mock.patch.object(bot, "LEDGER", ledger), \
                    mock.patch.object(bot, "insert_glossary_box", side_effect=lambda value: value), \
                    mock.patch.object(bot, "tags_for", return_value=["AI", "생성형 AI"]), \
                    mock.patch.object(
                        bot,
                        "generate_card",
                        return_value="/assets/img/thumb/ai-pricing-plan-comparison-guide.jpg",
                    ):
                with mock.patch.object(
                    bot, "mark_written", side_effect=OSError("disk full")
                ):
                    with self.assertRaisesRegex(RuntimeError, "게시물을 롤백"):
                        bot.publish(
                            self.topic, self.valid_post(), self.evidence, self.now
                        )
                self.assertEqual(
                    [name for name in os.listdir(posts) if name.endswith(".md")], []
                )

                filename = bot.publish(
                    self.topic, self.valid_post(), self.evidence, self.now
                )
                self.assertEqual(
                    [name for name in os.listdir(posts) if name.endswith(".md")],
                    [filename],
                )
                with open(ledger, encoding="utf-8") as handle:
                    written = json.load(handle)["written"]
                self.assertEqual(written[self.topic["id"]], filename[:-3])

    def test_publish_recovers_crash_left_post_without_creating_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            posts = os.path.join(directory, "posts")
            ledger = os.path.join(directory, "data", "written_topics.json")
            os.makedirs(posts)
            with mock.patch.object(bot, "POSTS_DIR", posts), \
                    mock.patch.object(bot, "LEDGER", ledger), \
                    mock.patch.object(bot, "insert_glossary_box", side_effect=lambda value: value), \
                    mock.patch.object(bot, "tags_for", return_value=["AI", "생성형 AI"]), \
                    mock.patch.object(
                        bot,
                        "generate_card",
                        return_value="/assets/img/thumb/ai-pricing-plan-comparison-guide.jpg",
                    ):
                existing = bot.save(
                    self.topic, self.valid_post(), self.evidence, self.now
                )
                with mock.patch.object(bot, "save") as save_again:
                    recovered = bot.publish(
                        self.topic, self.valid_post(), self.evidence, self.now
                    )
                save_again.assert_not_called()

            self.assertEqual(recovered, existing)
            self.assertEqual(
                [name for name in os.listdir(posts) if name.endswith(".md")],
                [existing],
            )
            with open(ledger, encoding="utf-8") as handle:
                self.assertEqual(
                    json.load(handle)["written"][self.topic["id"]],
                    existing[:-3],
                )


if __name__ == "__main__":
    unittest.main()
