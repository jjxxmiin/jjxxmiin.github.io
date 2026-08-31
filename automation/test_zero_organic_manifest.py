import datetime as dt
import unittest

import build_zero_organic_manifest as manifest


class ZeroOrganicManifestTests(unittest.TestCase):
    def test_fixed_window_contains_exactly_ninety_dates(self):
        self.assertEqual(
            manifest.inclusive_days(manifest.DEFAULT_START, manifest.DEFAULT_END),
            90,
        )

    def test_query_string_variants_collapse_to_the_public_path(self):
        rows = [
            {"landingPagePlusQueryString": "/posts/example/?utm=x", "sessions": "1"},
            {"landingPagePlusQueryString": "/posts/example/", "sessions": "2"},
            {"landingPagePlusQueryString": "/posts/no-session/", "sessions": "0"},
        ]
        self.assertEqual(manifest.paths_with_sessions(rows), {"/posts/example/"})

    def test_manifest_uses_strict_full_window_and_explicit_exclusion(self):
        inventory = [
            {
                "source": "_posts/2026-05-26-zero.md",
                "title": "zero",
                "date": "2026-05-26",
                "path": "/posts/zero/",
            },
            {
                "source": "_posts/2026-05-26-organic.md",
                "title": "organic",
                "date": "2026-05-26",
                "path": "/posts/organic/",
            },
            {
                "source": "_posts/2026-05-27-on-boundary.md",
                "title": "boundary",
                "date": "2026-05-27",
                "path": "/posts/on-boundary/",
            },
            {
                "source": next(iter(manifest.EXCLUDED_SOURCES)),
                "title": "excluded diagnostic",
                "date": "2020-01-01",
                "path": next(iter(manifest.EXCLUDED_PATHS)),
            },
        ]
        result = manifest.build_manifest(
            inventory,
            {"/posts/organic/"},
            property_id="123",
            start=dt.date(2026, 5, 27),
            end=dt.date(2026, 8, 24),
        )

        self.assertEqual(result["summary"]["eligible_full_window_posts"], 2)
        self.assertEqual(
            result["summary"]["eligible_posts_with_organic_landing_session"], 1
        )
        self.assertEqual(
            [target["source"] for target in result["targets"]],
            ["_posts/2026-05-26-zero.md"],
        )


if __name__ == "__main__":
    unittest.main()
