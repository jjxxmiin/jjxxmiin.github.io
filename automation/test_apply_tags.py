import unittest

import yaml

import apply_tags


class ApplyTagsTests(unittest.TestCase):
    def _rewrite(self, front_matter, tags):
        text = f"---{front_matter}\n---\n\n본문입니다.\n"
        parsed_front, original_body, ok = apply_tags.split_front_matter(text)
        self.assertTrue(ok)
        updated = apply_tags.write_tags(text, parsed_front, tags)
        updated_front, updated_body, ok = apply_tags.split_front_matter(updated)
        self.assertTrue(ok)
        self.assertEqual(updated_body, original_body)
        self.assertEqual(yaml.safe_load(updated_front)["tags"], tags)

    def test_replaces_indented_tag_sequence_without_leaving_old_items(self):
        self._rewrite(
            "\nlayout: post\ntags:\n  - 예전태그\n  - 중복후보\nsummary: 설명",
            ["LLM", "RAG"],
        )

    def test_replaces_unindented_safe_dump_tag_sequence(self):
        self._rewrite(
            "\nlayout: post\ntags:\n- 예전태그\n- 중복후보\nfaq:\n- question: 질문\n  answer: 답변",
            ["AI에이전트", "MCP"],
        )

    def test_unknown_future_topic_still_gets_two_controlled_tags(self):
        tags = apply_tags.tags_for("아직 분류되지 않은 새 주제", "", "Tech")
        self.assertGreaterEqual(len(tags), 2)
        self.assertEqual(len(tags), len(set(tags)))

    def test_comparison_operators_do_not_hide_following_prose(self):
        body = "오차는 0 < loss입니다. 다음 문단의 LLM 값이 > 1이면 중단합니다. <br>끝"
        cleaned = apply_tags.strip_noise(body)
        self.assertIn("0 < loss", cleaned)
        self.assertIn("LLM", cleaned)
        self.assertNotIn("<br>", cleaned)

    def test_generated_internal_links_do_not_change_topic_scoring(self):
        body = (
            "컴퓨터 비전 객체 탐지를 설명합니다.\n"
            "<!-- internal-links:start -->\n"
            "## 함께 읽기\n"
            "- Claude Code와 RAG, MCP, 음성 합성 글\n"
            "<!-- internal-links:end -->\n"
        )
        cleaned = apply_tags.strip_noise(body)
        self.assertIn("컴퓨터 비전", cleaned)
        self.assertNotIn("Claude Code", cleaned)


if __name__ == "__main__":
    unittest.main()
