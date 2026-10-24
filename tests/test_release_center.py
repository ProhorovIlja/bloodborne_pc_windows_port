"""Offline checks for the release history UI backend. No requests are sent."""
import io
import json
import tempfile
import unittest
from pathlib import Path

import paths  # noqa: F401 -- scripts on import path
import release_center as rc


def response(obj):
    def opener(request, timeout):
        assert request.full_url == rc.RELEASES_URL
        assert timeout == rc.update_check.TIMEOUT_S
        assert "Authorization" not in request.headers
        if isinstance(obj, Exception):
            raise obj
        return io.BytesIO(obj if isinstance(obj, bytes) else json.dumps(obj).encode("utf-8"))
    return opener


def release(tag="shyt-v0.7.3", preview=False, **kw):
    return {"draft": False, "prerelease": preview, "tag_name": tag,
            "name": "Stability fixes", "body": "Fixed party connection.",
            "html_url": f"https://github.com/{rc.REPO}/releases/tag/{tag}",
            "published_at": "2026-10-22T17:10:00Z", **kw}


class ReleaseCenterTests(unittest.TestCase):
    def test_stable_and_preview_channels(self):
        payload = [release(), release(tag="shyt-v0.7.4-rc.1", preview=True)]
        stable = rc.fetch_history(opener=response(payload))
        both = rc.fetch_history("preview", opener=response(payload))
        self.assertEqual([x["tag"] for x in stable], ["shyt-v0.7.3"])
        self.assertEqual(len(both), 2)
        self.assertTrue(both[1]["preview"])

    def test_fail_closed_on_bad_url_and_tag(self):
        r = release(html_url="https://evil.example/update.exe")
        self.assertEqual(rc.normalize_release(r)["url"], rc.RELEASES_PAGE)
        self.assertIsNone(rc.normalize_release(release(tag="v99.0.0")))
        self.assertIsNone(rc.normalize_release(release(tag="bbport-v99.0.0")))
        self.assertIsNone(rc.normalize_release(release(tag="shyt-v0.7.5-rc.1", preview=False)))
        self.assertIsNone(rc.normalize_release(release(tag="shyt-v0.7.5", preview=True)))
        self.assertIsNone(rc.normalize_release(release(tag="../../update.exe")))
        self.assertIsNone(rc.normalize_release(dict(release(), draft=True)))
        self.assertIsNone(rc.normalize_release(dict(release(), tag_name="bad")))
        with self.assertRaises(ValueError):
            rc.fetch_history("unstable", opener=response([]))

    def test_no_external_downloads_and_non_html_notes(self):
        suspicious = release(body="<script>do_bad_things()</script>\u0000\nText")
        items = rc.fetch_history(opener=response([suspicious]))
        self.assertIn("<script>", rc.format_history(items))  # raw inert text
        self.assertNotIn("\u0000", items[0]["notes"])
        self.assertNotIn("evil.example", items[0]["url"])

    def test_network_failure_and_large_body(self):
        self.assertEqual(rc.fetch_history(opener=response(OSError("offline"))), [])
        self.assertEqual(rc.fetch_history(opener=response([])), [])
        self.assertEqual(rc.fetch_history(opener=response(b"not json")), [])
        self.assertEqual(rc.fetch_history(opener=response(b"x" * (rc.MAX_RESPONSE + 12))), [])
        self.assertEqual(rc.fetch_history(opener=response({"message": "rate limited"})), [])
        long = rc.fetch_history(opener=response([release(body="X" * 20000)]))
        self.assertEqual(len(long[0]["notes"]), rc.MAX_BODY)
        self.assertIn("unavailable", rc.format_history([]))

    def test_local_changelog_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "CHANGELOG.md"
            self.assertIn("No bundled", rc.local_changelog(file))
            file.write_text("# Unreleased\nhello", encoding="utf-8")
            self.assertEqual(rc.local_changelog(file), "# Unreleased\nhello")
            file.write_bytes(b"x" * (rc.MAX_LOCAL + 1))
            self.assertIn("No bundled", rc.local_changelog(file))


if __name__ == "__main__":
    unittest.main()
