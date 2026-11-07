#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V446: bounded public GitHub ecosystem metadata inventory for SHYT integration.
No clones, binary artifacts, gameplay data, credentials, auto-merges or deployments.
Run in Actions with GITHUB_TOKEN read-only; token is never printed or persisted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

CORE = (
    "droogie/bbhost",
    "CLSAMG22/BBSC",
    "Amanises-Yharnam-Together/BBSC-Yharnam-Together",
    "Supermedo/bloodborne_pc",
    "deadinside28/bloodborne_pc",
    "Awakenchan/LanternEngine",
    "vladtepes22/NightwatchCoop",
    "visy/bloodborne_pc_windows_port",
    "Mrsuss60/bloodborne_pc_windows_port",
    "Wozzardman/shadp2p",
    "Wozzardman/shadnet-p2p",
    "shadps4-emu/shadPS4",
    "shadps4-emu/shadNet",
    "DarkIzuku/bloodborne_pc",
    "AdrianCsT/bloodborne_pc",
    "MaskZeus/bbbridge",
)
FORK_CANDIDATES = (
    "LRF17/LanternEngine-NativePlusHDR",
    "LRF17/NightwatchCoop-NativePlusHDR",
    "smilinleader/NightwatchCoop-BBFSS",
    "YoucefNabil/bbhost",
    "HatsyRei/bloodborne_pc_windows_port",
    "DarkIzuku/shadp2p",
    "oat018/shadp2p",
)
MAX_BRANCHES = 40
MAX_PRS = 15
MAX_FORKS = 15
API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json",
           "User-Agent": "SHYT-v446-public-ecosystem-watch",
           "X-GitHub-Api-Version": "2022-11-28"}

def validate() -> None:
    names = CORE + FORK_CANDIDATES
    if len(names) != len(set(names)) or len(names) > 64:
        raise ValueError("duplicate/oversized target list")
    for name in names:
        parts = name.split("/")
        if len(parts) != 2 or not all(p and all(c.isalnum() or c in "-_." for c in p) for p in parts):
            raise ValueError("bad GitHub repository name")

def request_json(path: str, token: str) -> object | None:
    if not path.startswith("/repos/") or "?" not in path and path.count("/") < 3:
        raise ValueError("refusing non-repository API path")
    req = urllib.request.Request(API + path, headers={
        **HEADERS, **({"Authorization": "Bearer " + token} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError("GitHub API HTTP " + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("GitHub API unreachable or malformed: " + type(exc).__name__) from None

def compact_pr(x: dict) -> dict:
    return {k: x.get(k) for k in ("number", "title", "state", "draft", "updated_at", "html_url")}

def scan(name: str, token: str, scan_fork_list: bool) -> dict:
    slug = urllib.parse.quote(name, safe="/")
    base = "/repos/" + slug
    info = request_json(base, token)
    if not isinstance(info, dict):
        raise RuntimeError("repo metadata unavailable")
    release = request_json(base + "/releases/latest", token)
    branches = request_json(base + "/branches?per_page=" + str(MAX_BRANCHES), token)
    prs = request_json(base + "/pulls?state=open&per_page=" + str(MAX_PRS) + "&sort=updated&direction=desc", token)
    forks = request_json(base + "/forks?per_page=" + str(MAX_FORKS) + "&sort=newest", token) if scan_fork_list else None
    if not isinstance(branches, list) or not isinstance(prs, list):
        raise RuntimeError("repo branch/PR metadata malformed")
    if forks is not None and not isinstance(forks, list):
        raise RuntimeError("fork metadata malformed")
    return {
        "repo": name,
        "default_branch": info.get("default_branch"),
        "pushed_at": info.get("pushed_at"),
        "fork": bool(info.get("fork")),
        "parent": (info.get("parent") or {}).get("full_name"),
        "archived": bool(info.get("archived")),
        "release": ({"tag": release.get("tag_name"),
                     "published_at": release.get("published_at"),
                     "url": release.get("html_url")} if isinstance(release, dict) else None),
        "branches_sample": [v.get("name") for v in branches if isinstance(v, dict)],
        "open_prs_sample": [compact_pr(v) for v in prs if isinstance(v, dict)],
        "forks_sample": [{"repo": v.get("full_name"), "pushed_at": v.get("pushed_at")}
                         for v in (forks or []) if isinstance(v, dict)],
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    validate()
    if a.self_test:
        assert len(CORE) >= 16 and len(FORK_CANDIDATES) >= 7
        assert MAX_BRANCHES <= 50 and MAX_PRS <= 30 and MAX_FORKS <= 20
        print("SHYT_V446_TARGETS_AND_BOUNDS_VALID")
        return 0
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN_REQUIRED_FOR_BOUNDED_PUBLIC_API_SCAN")
    out: dict = {
        "schema": "shyt-v446-public-github-metadata-v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "not_an_exhaustive_internet_search": True,
        "partial_results": True,
        "repositories": [],
        "errors": [],
    }
    for name in CORE + FORK_CANDIDATES:
        try:
            result = scan(name, token, name in CORE)
            out["repositories"].append(result)
            print("SHYT_V446_SCANNED", name, len(result["open_prs_sample"]),
                  len(result["branches_sample"]), len(result["forks_sample"]))
        except RuntimeError as exc:
            out["errors"].append({"repo": name, "error": str(exc)})
            print("SHYT_V446_SCAN_WARNING", name, str(exc)[:75])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("SHYT_V446_TOTAL", len(out["repositories"]), "ERRORS", len(out["errors"]))
    if len(out["repositories"]) < len(CORE):
        print("SHYT_V446_CORE_METADATA_INCOMPLETE")
        return 1
    print("SHYT_V446_CORE_FORK_BRANCH_PR_RELEASE_AUDIT_PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
