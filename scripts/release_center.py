"""Read-only, bounded GitHub release history for the Seamless Hunt Windows launcher.

- Only our fork's own GitHub release feed.
- No auto-install, asset downloads, credential collection or filesystem changes.
- Remote notes are rendered as plain text, not evaluated as HTML or Markdown.
- An unavailable feed never masquerades as "you have the latest version".
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import urllib.request

try:
    from . import update_check
except ImportError:
    import update_check

REPO = update_check.REPO
RELEASES_URL = f"https://api.github.com/repos/{REPO}/releases?per_page=8"
RELEASES_PAGE = update_check.RELEASES_PAGE
MAX_RESPONSE = 512 * 1024
MAX_BODY = 12_000
MAX_LOCAL = 64 * 1024
TAG_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-.](?:alpha|beta|rc)[.-]?\d+)?$", re.I)


def _clean_text(value, max_length=MAX_BODY):
    if not isinstance(value, str):
        return ""
    return "".join(ch if ch in "\n\t" or ord(ch) >= 32 else " " for ch in value)[:max_length]


def normalize_release(raw, channel="stable"):
    """Return validated, display-safe release metadata or None."""
    if not isinstance(raw, dict) or raw.get("draft") is not False:
        return None
    is_preview = raw.get("prerelease") is True
    if channel not in ("stable", "preview"):
        raise ValueError("Unsupported update channel")
    if channel == "stable" and is_preview:
        return None
    tag = raw.get("tag_name")
    if not isinstance(tag, str) or not TAG_RE.fullmatch(tag):
        return None
    # Only this fork's release page can open from the user interface.
    url = update_check.safe_release_url(raw.get("html_url"))
    published = raw.get("published_at")
    if not isinstance(published, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", published):
        published = ""
    return {
        "tag": tag,
        "title": _clean_text(raw.get("name") or tag, 120),
        "url": url,
        "published": published[:10],
        "notes": _clean_text(raw.get("body") or "No release notes supplied."),
        "preview": is_preview,
    }


def fetch_history(channel="stable", opener=None):
    """Return verified release metadata. [] means no data OR network unavailable.

    Display code must not equate empty result with "up to date".
    """
    if channel not in ("stable", "preview"):
        raise ValueError("Unsupported update channel")
    request = urllib.request.Request(
        RELEASES_URL, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "SeamlessHuntPC-ReleaseCenter",
        })
    try:
        with (opener or urllib.request.urlopen)(
                request, timeout=update_check.TIMEOUT_S) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            return []
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, list):
            return []
        out = []
        for item in data[:8]:
            release = normalize_release(item, channel=channel)
            if release is not None:
                out.append(release)
        return out
    except (OSError, ValueError, UnicodeError, TypeError, TimeoutError):
        return []


def local_changelog(path):
    """Local changelog for use when offline; text only and size-bounded."""
    try:
        file = Path(path)
        if not file.is_file() or file.stat().st_size > MAX_LOCAL:
            return "No bundled changelog for this build."
        return _clean_text(file.read_text(encoding="utf-8-sig"), MAX_LOCAL)
    except (OSError, UnicodeError):
        return "No bundled changelog for this build."


def format_history(releases):
    """Human-readable, plain-text history; no actions or downloads."""
    if not releases:
        return "Release history unavailable. You can try again or open the official Releases page."
    lines = []
    for item in releases:
        suffix = " (Preview)" if item["preview"] else ""
        title = item["title"]
        date = f"  |  {item['published']}" if item["published"] else ""
        lines.append(f"{item['tag']}{suffix}{date}\n{title}\n\n{item['notes']}")
    return "\n\n" + ("\n\n" + "─" * 40 + "\n\n").join(lines)
