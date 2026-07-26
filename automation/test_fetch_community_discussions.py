import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("fetch_community_discussions.py")
SPEC = importlib.util.spec_from_file_location("community_feed", MODULE_PATH)
assert SPEC and SPEC.loader
community_feed = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(community_feed)


class NormalizeDiscussionsTest(unittest.TestCase):
    def test_filters_announcements_sorts_and_minimizes(self):
        connections = [
            {
                "nodes": [
                    {
                        "number": 10,
                        "title": "  오래된   질문  ",
                        "url": "https://github.com/example/repo/discussions/10",
                        "createdAt": "2026-07-20T00:00:00Z",
                        "updatedAt": "2026-07-21T00:00:00Z",
                        "isAnswered": True,
                        "upvoteCount": 3,
                        "comments": {"totalCount": 4},
                        "author": {"login": "alice"},
                        "category": {"name": "Q&A", "slug": "q-a"},
                        "bodyHTML": "<script>not exported</script>",
                    },
                    {
                        "number": 11,
                        "title": "블로그 댓글",
                        "url": "https://github.com/example/repo/discussions/11",
                        "createdAt": "2026-07-22T00:00:00Z",
                        "updatedAt": "2026-07-24T00:00:00Z",
                        "isAnswered": False,
                        "upvoteCount": 0,
                        "comments": {"totalCount": 1},
                        "author": {"login": "bob"},
                        "category": {
                            "name": "Announcements",
                            "slug": "announcements",
                        },
                    },
                ]
            },
            {
                "nodes": [
                    {
                        "number": 12,
                        "title": "최신 토론",
                        "url": "https://github.com/example/repo/discussions/12",
                        "createdAt": "2026-07-23T00:00:00Z",
                        "updatedAt": "2026-07-25T00:00:00Z",
                        "isAnswered": False,
                        "upvoteCount": 1,
                        "comments": {"totalCount": 2},
                        "author": None,
                        "category": {"name": "General", "slug": "general"},
                    }
                ]
            },
        ]

        result = community_feed.normalize_discussions(
            connections, {"q-a", "general"}, limit=12
        )

        self.assertEqual([item["number"] for item in result], [12, 10])
        self.assertEqual(result[0]["author"], "ghost")
        self.assertEqual(result[1]["title"], "오래된 질문")
        self.assertTrue(result[1]["answered"])
        self.assertNotIn("bodyHTML", result[1])

    def test_enforces_limit(self):
        nodes = [
            {
                "number": number,
                "title": f"토론 {number}",
                "url": f"https://github.com/example/repo/discussions/{number}",
                "createdAt": f"2026-07-{number:02d}T00:00:00Z",
                "updatedAt": f"2026-07-{number:02d}T00:00:00Z",
                "isAnswered": False,
                "upvoteCount": 0,
                "comments": {"totalCount": 0},
                "author": {"login": "user"},
                "category": {"name": "General", "slug": "general"},
            }
            for number in range(1, 6)
        ]

        result = community_feed.normalize_discussions(
            [{"nodes": nodes}], {"general"}, limit=2
        )

        self.assertEqual([item["number"] for item in result], [5, 4])


class BuildQueryTest(unittest.TestCase):
    def test_builds_one_connection_per_category(self):
        query = community_feed.build_discussions_query(3)

        self.assertIn("$category0: ID!", query)
        self.assertIn("category2: discussions(", query)
        self.assertEqual(query.count("categoryId:"), 3)


if __name__ == "__main__":
    unittest.main()
