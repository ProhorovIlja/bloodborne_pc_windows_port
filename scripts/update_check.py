"""Launcher update notice: is a newer bbport release out?

  check(current_version, cache_file)  -> Notice or None

Asks GitHub's public API (no token) for the latest release of THIS Seamless Hunt fork, at most once every
6 hours (the answer is cached in cache_file), with a 3 s timeout. Offline, a timeout, a rate limit
or an unexpected answer: no notice, nothing raised (the cached answer is used while it is fresh).
A party needs the same bbport version on every PC (docs/party/version_check.md), so the notice
says so.
"""
import json
import re
import time
import urllib.request
from urllib.parse import urlsplit
from pathlib import Path

# Seamless Hunt has its own release channel. Upstream visy releases are not
# automatically compatible with a Seamless Hunt native-client build.
REPO = "ProhorovIlja/bloodborne_pc_windows_port"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases?per_page=16"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
CACHE_SECONDS = 6 * 3600
FAILED_CACHE_SECONDS = 1800  # offline / no answer: ask again after 30 min, not on every start
TIMEOUT_S = 3.0
MAX_RESPONSE = 512 * 1024
# Dedicated Seamless Hunt client builds only. Generic bbport releases are not interchangeable.
PROJECT_TAG_RE = re.compile(r"^shyt-v([0-9]{1,5})\.([0-9]{1,5})\.([0-9]{1,5})$", re.I)


def safe_release_url(value):
    """Accept only tag/release pages in our OWN HTTPS GitHub repository."""
    if not isinstance(value, str):
        return RELEASES_PAGE
    try:
        url = urlsplit(value)
    except ValueError:
        return RELEASES_PAGE
    allowed_prefix = f"/{REPO}/releases"
    path = url.path.rstrip("/")
    if (url.scheme != "https" or url.netloc.lower() != "github.com"
            or url.username or url.password or url.query or url.fragment
            or (path != allowed_prefix and not path.startswith(allowed_prefix + "/tag/"))):
        return RELEASES_PAGE
    return value


class Notice:
    def __init__(self, version, url):
        self.version = version
        self.url = url

    @property
    def text(self):
        return f"Version {self.version} is out — every PC in the party needs the same version"


def parse_version(text):
    """'v0.6.2' / '0.6.2' / 'bbport 0.6.2 (...)' -> (0, 6, 2); None when there is no version."""
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", str(text or ""))
    if not m:
        return None
    return tuple(int(g or 0) for g in m.groups())


def newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    return bool(a and b and a > b)


def fetch(url=LATEST_URL, timeout=TIMEOUT_S, opener=None):
    """Find the newest STABLE Seamless Hunt release; ignore unrelated bbport tags.

    GitHub /releases/latest may point to a generic port release, even if our
    own compatible builds exist. Only purpose-tagged releases are candidates.
    This is still a read-only notice, NOT proof of protocol compatibility.
    """
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "bbport-launcher"})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=timeout) as r:
            body = r.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            return None
        releases = json.loads(body.decode("utf-8"))
    except (OSError, ValueError, UnicodeError, TimeoutError, TypeError):
        return None
    if not isinstance(releases, list):
        return None
    selected = None
    for entry in releases[:16]:
        if not isinstance(entry, dict):
            continue
        if entry.get("draft") is not False or entry.get("prerelease") is not False:
            continue
        tag = entry.get("tag_name")
        if not isinstance(tag, str):
            continue
        match = PROJECT_TAG_RE.fullmatch(tag)
        if not match:
            continue
        version = tuple(int(n) for n in match.groups())
        if selected is None or version > selected[0]:
            # The release-specific link must actually point to THIS tag.
            page = safe_release_url(entry.get("html_url"))
            expected = f"{RELEASES_PAGE}/tag/{tag}"
            selected = (version, {"tag": tag,
                                  "url": page if page == expected else RELEASES_PAGE})
    return selected[1] if selected else None


def _read_cache(cache_file, now):
    try:
        c = json.loads(Path(cache_file).read_text(encoding="utf-8"))
        if not isinstance(c, dict):
            return None
        keep = CACHE_SECONDS if c.get("latest") else FAILED_CACHE_SECONDS
        if 0 <= now - float(c.get("checked", 0)) < keep:
            return c
    except (OSError, ValueError, TypeError):
        pass
    return None


def check(current_version, cache_file, now=None, fetcher=fetch):
    """The notice to show, or None. Never raises."""
    now = time.time() if now is None else now
    try:
        cached = _read_cache(cache_file, now)
        if cached is not None:
            latest = cached.get("latest")
        else:
            latest = fetcher()
            try:
                Path(cache_file).write_text(json.dumps({"checked": now, "latest": latest}), encoding="utf-8")
            except OSError:
                pass
        if (isinstance(latest, dict) and isinstance(latest.get("tag"), str)
                and PROJECT_TAG_RE.fullmatch(latest["tag"])
                and newer(latest["tag"], current_version)):
            version = ".".join(map(str, parse_version(latest["tag"])))
            return Notice(version, safe_release_url(latest.get("url")))
    except Exception:
        pass
    return None
