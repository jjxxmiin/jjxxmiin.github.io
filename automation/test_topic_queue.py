import json
import tempfile
import unittest
from unittest import mock

import build_topic_queue as queue
import guide_bot


class TopicQueueTests(unittest.TestCase):
    def test_purchase_queries_score_above_generic_how_to(self):
        purchase = queue.commercial_value("클로드 코드 가격")
        how_to = queue.commercial_value("클로드 코드 사용법")
        self.assertGreater(purchase[0], how_to[0])
        self.assertEqual(purchase[1], "구매·구독 판단")

    def test_comparison_topics_wait_for_firsthand_testing(self):
        topics = queue.build()
        comparisons = [topic for topic in topics if topic["format"] == "비교와 추천"]
        self.assertTrue(comparisons)
        self.assertTrue(all(
            topic["publication_mode"] == "manual_test" for topic in comparisons
        ))

    def test_price_and_how_to_topics_remain_automatable(self):
        topics = queue.build()
        automatic = [
            topic for topic in topics
            if topic["publication_mode"] == "auto_research"
        ]
        self.assertTrue(automatic)
        self.assertTrue(all(topic["format"] != "비교와 추천" for topic in automatic))

    def test_guide_picker_skips_manual_comparison_topic(self):
        rows = {
            "topics": [
                {
                    "id": "comparison",
                    "status": "pending",
                    "publication_mode": "manual_test",
                },
                {
                    "id": "price",
                    "status": "pending",
                    "publication_mode": "auto_research",
                },
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as handle:
            json.dump(rows, handle)
            handle.flush()
            with mock.patch.object(guide_bot, "QUEUE", handle.name):
                self.assertEqual(guide_bot.pick_topic(None)["id"], "price")
                with self.assertRaises(SystemExit):
                    guide_bot.pick_topic("comparison")


if __name__ == "__main__":
    unittest.main()
