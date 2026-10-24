"""scripts/update_check.py: the launcher's update notice (mocked GitHub answers, no network)."""
import paths  # noqa: F401  (puts scripts/ on sys.path)
import io
import json
import tempfile
import unittest
from pathlib import Path

import update_check as uc


def answer(obj):
    """An opener for fetch(): returns obj as the HTTP body (or raises it)."""
    def opener(req, timeout):
        assert req.full_url == uc.LATEST_URL and timeout == uc.TIMEOUT_S
        assert "Authorization" not in req.headers
        if isinstance(obj, Exception):
            raise obj
        return io.BytesIO(obj if isinstance(obj, bytes) else json.dumps([obj] if isinstance(obj, dict) and "tag_name" in obj else obj).encode())
    return opener


RELEASE = {"tag_name": "shyt-v0.6.3", "html_url": "https://github.com/ProhorovIlja/bloodborne_pc_windows_port/releases/tag/shyt-v0.6.3",
           "draft": False, "prerelease": False}


class UpdateCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name) / "update_check.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_versions(self):
        self.assertEqual(uc.parse_version("v0.6.2"), (0, 6, 2))
        self.assertEqual(uc.parse_version("0.6.1 (0.6.1-12-gabc)"), (0, 6, 1))
        self.assertEqual(uc.parse_version("0.7"), (0, 7, 0))
        self.assertIsNone(uc.parse_version("latest"))
        self.assertTrue(uc.newer("v0.6.10", "0.6.9"))
        self.assertFalse(uc.newer("v0.6.1", "0.6.1"))
        self.assertFalse(uc.newer("v0.6.0", "0.6.1"))
        self.assertFalse(uc.newer("junk", "0.6.1"))

    def test_fetch_parses_and_rejects(self):
        self.assertEqual(uc.fetch(opener=answer(RELEASE)), {"tag": "shyt-v0.6.3", "url": RELEASE["html_url"]})
        self.assertIsNone(uc.fetch(opener=answer(dict(RELEASE, prerelease=True))))
        self.assertIsNone(uc.fetch(opener=answer(b"<html>rate limited</html>")))
        self.assertIsNone(uc.fetch(opener=answer(OSError("offline"))))
        self.assertIsNone(uc.fetch(opener=answer(TimeoutError())))
        self.assertIsNone(uc.fetch(opener=answer({"message": "API rate limit exceeded"})))
        # a link elsewhere is never shown: the release page instead
        self.assertEqual(uc.fetch(opener=answer(dict(RELEASE, html_url="https://evil.example/x")))["url"],
                         uc.RELEASES_PAGE)
        # A different GitHub repository, a prefix-trick URL or credentials
        # must NEVER be used as a clickable update destination.
        for bad_url in (
            "https://github.com/visy/bloodborne_pc_windows_port/releases/tag/v9.0.0",
            "https://github.com/ProhorovIlja/bloodborne_pc_windows_port-evil/releases/tag/v9",
            "https://github.com@evil.example/ProhorovIlja/bloodborne_pc_windows_port/releases",
            "http://github.com/ProhorovIlja/bloodborne_pc_windows_port/releases",
            "https://github.com/ProhorovIlja/bloodborne_pc_windows_port/releases?download=https://bad",
        ):
            with self.subTest(bad_url=bad_url):
                self.assertEqual(uc.fetch(opener=answer(dict(RELEASE, html_url=bad_url)))["url"],
                                 uc.RELEASES_PAGE)
                self.assertEqual(uc.safe_release_url(bad_url), uc.RELEASES_PAGE)

    def test_only_release_channel_tags_and_highest_stable_version(self):
        # A normal native bbport release can exist in the SAME GitHub repo.
        generic = dict(RELEASE, tag_name="v99.0.0")
        older = dict(RELEASE, tag_name="shyt-v0.6.1",
                     html_url=uc.RELEASES_PAGE + "/tag/shyt-v0.6.1")
        newer = dict(RELEASE, tag_name="shyt-v0.6.10",
                     html_url=uc.RELEASES_PAGE + "/tag/shyt-v0.6.10")
        preview = dict(RELEASE, tag_name="shyt-v7.0.0-rc.1",
                       prerelease=True)
        self.assertEqual(uc.fetch(opener=answer([generic, older, preview, newer])),
                         {"tag": "shyt-v0.6.10", "url": newer["html_url"]})
        self.assertIsNone(uc.fetch(opener=answer([generic])))
        self.assertIsNone(uc.fetch(opener=answer(dict(RELEASE, draft=True))))
        self.assertIsNone(uc.fetch(opener=answer(b"x" * (uc.MAX_RESPONSE + 1))))

    def test_different_tag_same_repo_cannot_redirect(self):
        url = uc.RELEASES_PAGE + "/tag/shyt-v9.9.9"
        release = dict(RELEASE, html_url=url)
        self.assertEqual(uc.fetch(opener=answer(release))["url"], uc.RELEASES_PAGE)

    def test_cached_update_does_not_link_to_old_upstream(self):
        self.cache.write_text(json.dumps({
            "checked": 100.0,
            "latest": {
                "tag": "v0.9.9",
                "url": "https://github.com/visy/bloodborne_pc_windows_port/releases/tag/v0.9.9"
            }
        }), encoding="utf-8")
        # Stale caches from the original Windows port are no longer valid.
        notice = uc.check("0.7.2", self.cache, now=200.0)
        self.assertIsNone(notice)

    def test_notice_and_cache(self):
        calls = []

        def fetcher():
            calls.append(1)
            return uc.fetch(opener=answer(RELEASE))
        n = uc.check("0.6.2", self.cache, now=1000.0, fetcher=fetcher)
        self.assertEqual(n.version, "0.6.3")
        self.assertEqual(n.text, "Version 0.6.3 is out — every PC in the party needs the same version")
        self.assertIn("releases/tag/shyt-v0.6.3", n.url)
        # cached for 6 h: no second request
        self.assertIsNotNone(uc.check("0.6.2", self.cache, now=1000.0 + 5 * 3600, fetcher=fetcher))
        self.assertEqual(len(calls), 1)
        uc.check("0.6.2", self.cache, now=1000.0 + 6 * 3600 + 1, fetcher=fetcher)
        self.assertEqual(len(calls), 2)
        # up to date: no notice
        self.assertIsNone(uc.check("0.6.3", self.cache, now=1000.0 + 6 * 3600 + 2, fetcher=fetcher))

    def test_offline_is_quiet_and_retried_later(self):
        calls = []

        def offline():
            calls.append(1)
            return uc.fetch(opener=answer(OSError("no network")))
        self.assertIsNone(uc.check("0.6.2", self.cache, now=0.0, fetcher=offline))
        self.assertIsNone(uc.check("0.6.2", self.cache, now=600.0, fetcher=offline))
        self.assertEqual(len(calls), 1)
        self.assertIsNone(uc.check("0.6.2", self.cache, now=1801.0, fetcher=offline))
        self.assertEqual(len(calls), 2)

    def test_broken_cache_and_fetcher_never_raise(self):
        self.cache.write_text("{not json", encoding="utf-8")

        def boom():
            raise RuntimeError("x")
        self.assertIsNone(uc.check("0.6.2", self.cache, now=0.0, fetcher=boom))
        self.cache.write_text("[1, 2]", encoding="utf-8")
        self.assertIsNone(uc.check("0.6.2", self.cache, now=0.0, fetcher=boom))
        # a cache that cannot be written: the notice still shows
        n = uc.check("0.6.2", Path(self.tmp.name) / "no" / "dir" / "c.json", now=0.0,
                     fetcher=lambda: {"tag": "shyt-v9.0.0", "url": uc.RELEASES_PAGE})
        self.assertEqual(n.version, "9.0.0")


if __name__ == "__main__":
    unittest.main()
