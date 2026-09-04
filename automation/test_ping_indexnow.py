import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock

from automation import ping_indexnow as indexnow


class EndpointTests(unittest.TestCase):
    def test_uses_official_indexnow_endpoints(self):
        self.assertEqual(
            indexnow.ENDPOINTS["naver"],
            "https://searchadvisor.naver.com/indexnow",
        )
        self.assertEqual(
            indexnow.ENDPOINTS["bing"],
            "https://www.bing.com/indexnow",
        )


class _Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]


class GlobalSeoDetectionTests(unittest.TestCase):
    def test_current_global_seo_files_are_detected(self):
        paths = [
            "_config.yml",
            "_includes/head.html",
            "_layouts/default.html",
            "_layouts/home.html",
            "_layouts/post.html",
            "sitemap.xml",
            "assets/robots.txt",
            "llms.txt",
            "llms-full.txt",
        ]

        self.assertTrue(indexnow.has_global_seo_change(paths))
        for path in paths:
            self.assertTrue(indexnow.is_global_seo_file(path), path)
        self.assertFalse(indexnow.is_global_seo_file("_posts/2026-09-04-new.md"))

    def test_changed_files_falls_back_when_requested_base_is_unavailable(self):
        with mock.patch.object(
            indexnow,
            "_all_diff",
            side_effect=[OSError("shallow clone"), "_includes/head.html\n"],
        ) as diff, redirect_stdout(io.StringIO()):
            paths = indexnow.changed_files("missing-base")

        self.assertEqual(paths, ["_includes/head.html"])
        self.assertEqual(diff.call_args_list[1].args, ("HEAD~1",))


class SitemapTests(unittest.TestCase):
    def test_reads_only_page_locs_from_namespaced_urlset(self):
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
          <url>
            <loc>https://www.opsoai.com/posts/one/</loc>
            <image:image><image:loc>https://cdn.example.com/one.jpg</image:loc></image:image>
          </url>
          <url><loc>https://www.opsoai.com/posts/two/</loc></url>
        </urlset>"""

        with mock.patch.object(
            indexnow.urllib.request,
            "urlopen",
            return_value=_Response(xml),
        ) as urlopen:
            urls = indexnow.fetch_deployed_sitemap("https://www.opsoai.com")

        self.assertEqual(urls, [
            "https://www.opsoai.com/posts/one/",
            "https://www.opsoai.com/posts/two/",
        ])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://www.opsoai.com/sitemap.xml")

    def test_malformed_xml_returns_none_for_post_only_fallback(self):
        with mock.patch.object(
            indexnow.urllib.request,
            "urlopen",
            return_value=_Response(b"<urlset><url>"),
        ), redirect_stdout(io.StringIO()) as output:
            urls = indexnow.fetch_deployed_sitemap("https://www.opsoai.com")

        self.assertIsNone(urls)
        self.assertIn("XML 파싱 실패", output.getvalue())

    def test_sanitizes_host_https_duplicates_fragments_and_caps_at_10000(self):
        raw = [
            "https://WWW.OPSOAI.COM/first/",
            "https://www.opsoai.com/first/",
            "http://www.opsoai.com/insecure/",
            "https://other.example/foreign/",
            "https://www.opsoai.com/fragment/#part",
        ]
        raw.extend(
            f"https://www.opsoai.com/posts/{number}/"
            for number in range(indexnow.MAX_URLS + 2)
        )

        with redirect_stdout(io.StringIO()) as output:
            urls = indexnow.sanitize_urls(raw, "www.opsoai.com")

        self.assertEqual(indexnow.MAX_URLS, 10_000)
        self.assertEqual(len(urls), indexnow.MAX_URLS)
        self.assertEqual(urls[0], "https://www.opsoai.com/first/")
        self.assertEqual(len(urls), len(set(urls)))
        self.assertNotIn("http://www.opsoai.com/insecure/", urls)
        self.assertIn("요청 상한 10,000건", output.getvalue())


class MainFlowTests(unittest.TestCase):
    def _run_main(
        self,
        *,
        argv=None,
        changed_files=None,
        changed_posts=None,
        sitemap_urls=None,
        live=True,
    ):
        submit = mock.Mock(return_value=True)
        is_live = mock.Mock(return_value=live)
        fetch = mock.Mock(return_value=sitemap_urls)
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", argv or ["ping_indexnow.py"]), \
             mock.patch.dict(os.environ, {"INDEXNOW_BASE": "base-sha"}), \
             mock.patch.object(indexnow, "site_url", return_value="https://www.opsoai.com"), \
             mock.patch.object(indexnow, "changed_files", return_value=changed_files or []), \
             mock.patch.object(indexnow, "changed_posts", return_value=changed_posts or []), \
             mock.patch.object(indexnow, "fetch_deployed_sitemap", fetch), \
             mock.patch.object(indexnow, "is_live", is_live), \
             mock.patch.object(indexnow, "find_key", return_value="test-indexnow-key"), \
             mock.patch.object(indexnow, "ENDPOINTS", {"test": "https://indexnow.test"}), \
             mock.patch.object(indexnow, "submit", submit), \
             redirect_stdout(stdout):
            indexnow.main()
        return stdout.getvalue(), fetch, is_live, submit

    def test_global_change_submits_deployed_sitemap_without_per_url_head(self):
        output, fetch, is_live, submit = self._run_main(
            changed_files=["_includes/head.html", "_posts/2026-09-04-new.md"],
            changed_posts=["_posts/2026-09-04-new.md"],
            sitemap_urls=[
                "https://www.opsoai.com/",
                "https://www.opsoai.com/posts/one/",
                "https://www.opsoai.com/posts/one/",
                "http://www.opsoai.com/insecure/",
                "https://other.example/foreign/",
            ],
        )

        fetch.assert_called_once_with("https://www.opsoai.com")
        is_live.assert_not_called()
        submit.assert_called_once()
        payload = submit.call_args.args[2]
        self.assertEqual(payload["host"], "www.opsoai.com")
        self.assertEqual(payload["urlList"], [
            "https://www.opsoai.com/",
            "https://www.opsoai.com/posts/one/",
        ])
        self.assertIn("전역 SEO 변경 감지", output)
        self.assertIn("배포 sitemap canonical URL 2건", output)

    def test_sitemap_failure_falls_back_to_existing_post_live_check(self):
        output, fetch, is_live, submit = self._run_main(
            changed_files=["sitemap.xml", "_posts/2026-09-04-new-post.md"],
            changed_posts=["_posts/2026-09-04-new-post.md"],
            sitemap_urls=None,
        )

        fetch.assert_called_once()
        is_live.assert_called_once_with(
            "https://www.opsoai.com/posts/new-post/"
        )
        payload = submit.call_args.args[2]
        self.assertEqual(
            payload["urlList"],
            ["https://www.opsoai.com/posts/new-post/"],
        )
        self.assertIn("변경된 포스트 URL만 제출", output)

    def test_post_only_change_keeps_old_flow_and_does_not_fetch_sitemap(self):
        _, fetch, is_live, submit = self._run_main(
            changed_files=["_posts/2026-09-04-post-only.md"],
            changed_posts=["_posts/2026-09-04-post-only.md"],
        )

        fetch.assert_not_called()
        is_live.assert_called_once_with(
            "https://www.opsoai.com/posts/post-only/"
        )
        self.assertEqual(
            submit.call_args.args[2]["urlList"],
            ["https://www.opsoai.com/posts/post-only/"],
        )

    def test_dry_run_fetches_global_sitemap_but_never_heads_or_submits(self):
        output, fetch, is_live, submit = self._run_main(
            argv=["ping_indexnow.py", "--dry-run"],
            changed_files=["_layouts/post.html"],
            sitemap_urls=["https://www.opsoai.com/posts/one/"],
        )

        fetch.assert_called_once()
        is_live.assert_not_called()
        submit.assert_not_called()
        self.assertIn("--dry-run: 실제 요청은 보내지 않았습니다.", output)


if __name__ == "__main__":
    unittest.main()
