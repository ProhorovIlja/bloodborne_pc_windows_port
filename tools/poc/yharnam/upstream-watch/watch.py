#!/usr/bin/env python3
"""Bloodborne cross-fork source monitor (GitHub read-only; never auto-cherry-pick).

Compares 8 source HEADs, latest releases and 22 cross-fork PRs against a manually
reviewed inventory. Writes JSON and Markdown in the output folder; never
writes to GitHub, tests locally only, and cannot touch game/server state.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REGISTRY = Path(__file__).with_name("sources.json")
API = "https://api.github.com"
SAFE_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHORT_SHA = re.compile(r"^[0-9a-f]{40}$")


def fetch(path: str, token: str = "") -> dict:
    if not path.startswith("/repos/") or ".." in path or "?" in path:
        raise ValueError("Only fixed public repository REST paths are allowed")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BBSC-upstream-audit-readonly-2026",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    with urlopen(Request(API + path, headers=headers), timeout=15) as response:
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("Unexpected public GitHub API response")
    return data


def load_inventory(path: Path = REGISTRY) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or len(data.get("repositories", [])) < 6:
        raise ValueError("Incomplete cross-fork inventory; refuse")
    if data.get("policy") != "REPORT_ONLY_NEVER_AUTOMATICALLY_IMPORT_OR_DEPLOY":
        raise ValueError("Auto deployment cannot be part of an upstream monitor")
    repo_names = set()
    for row in data["repositories"]:
        name = row["full_name"]
        if not SAFE_REPO.fullmatch(name) or name in repo_names:
            raise ValueError("Invalid or duplicate source repository")
        repo_names.add(name)
        if not SHORT_SHA.fullmatch(row["known_head"]):
            raise ValueError("Pinned review SHA required")
        if not row["known_release_tag"] or not row["compatibility"]:
            raise ValueError("Inventory must name release and compatibility constraint")
    seen = set()
    for row in data.get("pull_requests", []):
        key = (row["repo"], row["number"])
        if row["repo"] not in repo_names or not isinstance(row["number"], int) or row["number"] < 1:
            raise ValueError("Only validated repository PR IDs allowed")
        if key in seen or row["last_seen"] not in ("open", "closed", "merged"):
            raise ValueError("Duplicate PR or invalid expected state")
        seen.add(key)
    return data


def status_of_pr(item: dict) -> str:
    return "merged" if item.get("merged_at") else item.get("state", "unknown")


def _attempt(get, endpoint: str, failures: list[dict]) -> dict | None:
    try:
        return get(endpoint)
    except (OSError, HTTPError, URLError, ValueError, KeyError, TimeoutError) as ex:
        # Exceptions can include URL headers. Never put credentials in report/log.
        failures.append({"endpoint": endpoint, "error_type": type(ex).__name__})
        return None


def survey(registry: dict, get) -> dict:
    output = {
        "schema": 1,
        "measured_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "baseline_pin": registry["pinned_yt_game_server"],
        "safety": registry["policy"],
        "repositories": [],
        "pull_requests": [],
        "errors": [],
    }
    for entry in registry["repositories"]:
        name = entry["full_name"]
        commit = _attempt(get, "/repos/" + name + "/commits/HEAD", output["errors"])
        release = _attempt(get, "/repos/" + name + "/releases/latest", output["errors"])
        head = commit.get("sha", "") if commit else ""
        tag = release.get("tag_name", "") if release else ""
        output["repositories"].append({
            "repo": name,
            "category": entry["category"],
            "compatibility": entry["compatibility"],
            "reviewed_head": entry["known_head"],
            "observed_head": head,
            "head_changed": bool(head and head != entry["known_head"]),
            "reviewed_release": entry["known_release_tag"],
            "observed_release": tag,
            "release_changed": bool(tag and tag != entry["known_release_tag"]),
            "evidence_complete": bool(head and tag),
            "url": "https://github.com/" + name,
        })
    for entry in registry["pull_requests"]:
        repo, n = entry["repo"], entry["number"]
        item = _attempt(get, "/repos/" + repo + "/pulls/" + str(n), output["errors"])
        state = status_of_pr(item) if item else "unavailable"
        output["pull_requests"].append({
            "repo": repo, "number": n, "area": entry["area"],
            "priority": entry["priority"], "next_action": entry["action"],
            "reviewed_state": entry["last_seen"], "observed_state": state,
            "state_changed": state not in ("unavailable", entry["last_seen"]),
            "merge_commit": item.get("merge_commit_sha") if item and state == "merged" else None,
            "url": "https://github.com/" + repo + "/pull/" + str(n),
        })
    return output


def md_safe(s) -> str:
    return str(s if s is not None else "").replace("|", "/").replace("\n", " ").replace("\r", " ")


def markdown(report: dict) -> str:
    lines = [
        "# Cross-fork Bloodborne upstream watch",
        "",
        "Snapshot UTC: " + report["measured_utc"],
        "",
        "**READ-ONLY EVIDENCE. No changes imported, merged, deployed or enabled.**",
        "Source pin for official YT1.3 testing: " + report["baseline_pin"],
        "",
        "## Repositories",
        "",
        "| Source | Reviewed release → observed | SHA drift? | Porting constraint |",
        "|---|---|---|---|",
    ]
    for r in report["repositories"]:
        lines.append("| " + md_safe(r["repo"]) + " | " +
                     md_safe(r["reviewed_release"]) + " → " +
                     md_safe(r["observed_release"] or "unavailable") + " | " +
                     ("YES REVIEW REQUIRED" if r["head_changed"] else
                      ("unchanged" if r["evidence_complete"] else "unknown")) + " | " +
                     md_safe(r["compatibility"]) + " |")
    lines += ["", "## Reviewed native Bloodborne cross-fork PR watch", "",
              "| PR | Area | Old → current | Priority | Gate |",
              "|---|---|---|---|---|"]
    for p in report["pull_requests"]:
        status = p["reviewed_state"] + " → " + p["observed_state"]
        if p["state_changed"]:
            status += " (REVIEW)"
        lines.append("| [#" + str(p["number"]) + "](" + p["url"] + ") | " +
                     md_safe(p["area"]) + " | " + md_safe(status) + " | " +
                     md_safe(p["priority"]) + " | " + md_safe(p["next_action"]) + " |")
    lines += [
        "",
        "## Import gates (always manual)",
        "",
        "1. Confirm source owner/licence, precise commit, game version, runtime and platform.",
        "2. Check YT1.3 wire compatibility and auth, host authority, password/team boundaries.",
        "3. Adapt behind a feature flag, with relevant unit/integration tests and rollback.",
        "4. Build native C++/launcher in disposable CI and check 4-player join + 32/64 load.",
        "5. Two-PC tests with real saves backed up; only then propose promotion.",
        "6. Never change Fornex/CLS Friends, master, accounts or existing saves from this job.",
        "",
        "Failed API requests (metadata only, never credentials): " +
        str(len(report["errors"])) + ".",
        "Missing evidence is UNKNOWN, never interpreted as no updates.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=REGISTRY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = load_inventory(args.inventory)
    token = os.environ.get("GITHUB_TOKEN", "")
    report = survey(config, lambda path: fetch(path, token))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "upstreams.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output / "UPSTREAMS.md").write_text(markdown(report), encoding="utf-8")
    changes = sum(r["head_changed"] or r["release_changed"] for r in report["repositories"])
    changes += sum(p["state_changed"] for p in report["pull_requests"])
    print("BLOODBORNE_CROSS_FORK_READ_ONLY_AUDIT sources=" +
          str(len(report["repositories"])) + " prs=" +
          str(len(report["pull_requests"])) + " changes_to_review=" + str(changes) +
          " unavailable=" + str(len(report["errors"])))
    if report["errors"]:
        print("Upstream metadata incomplete, see report; do not assume no changes.",
              file=sys.stderr)
    return 0  # never block gameplay development on transient public REST failure


if __name__ == "__main__":
    raise SystemExit(main())
