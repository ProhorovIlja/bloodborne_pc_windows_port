#!/usr/bin/env python3
"""Read-only, byte-bounded GitHub Actions diagnostics and workflow audit.

Never requests Actions log archives or job log endpoints. Public PR branches
are inspected as DATA: no checkout, execution, shell, eval or dynamic imports.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPORT_BYTES = 16_384
API_BYTES = 1_048_576
WORKFLOW_BYTES = 65_536
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
WORKFLOW_SUFFIX = (".yml", ".yaml")

# A signal here indicates a possible unsafe output, NOT a proven runtime bug.
DIRECT_LOG = re.compile(
    r"fetch_workflow_job_logs|fetch_workflow_run_logs|"
    r"(?:/actions/(?:runs|jobs)/[^\s'\"}]+/logs(?:\b|[/?]))|"
    r"gh\s+run\s+view\s+[^\n]*--log(?:-failed)?\b|"
    r"gh\s+run\s+download\s+[^\n]*logs",
    re.I,
)
UNBOUNDED_CAT = re.compile(
    r"(?:^|[;&|]\s*|\brun:\s*)(?:cat|type)\s+(?![<>])[^#\n]{0,140}\.(?:log|trace|out)\b|"
    r"\bGet-Content\s+(?:-Raw\s+)?[^#\n]{0,140}\.(?:log|trace|out)\b",
    re.I,
)
UNBOUNDED_TEE = re.compile(r"\btee\s+(?:-[A-Za-z]+\s+)?[^\n#]{0,120}\.(?:log|trace|out)\b", re.I)
TAIL_COUNT = re.compile(r"\btail\s+(?:-n\s*|--lines(?:=|\s+))([0-9]+)\b", re.I)
UNBOUNDED_DIFF = re.compile(r"^\s*(?:run:\s*)?git\s+(?:-C\s+\S+\s+)?(?:diff|show)\b", re.I)
SAFE_DIFF = re.compile(r"--(?:check|stat|numstat|name-only|name-status)\b", re.I)


def scan_workflow(path: str, source: str) -> list[dict]:
    findings = []
    for index, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        rule, severity = None, None
        if DIRECT_LOG.search(line):
            rule, severity = "raw-actions-log-download", "critical"
        elif UNBOUNDED_CAT.search(line):
            rule, severity = "unbounded-log-dump", "high"
        elif UNBOUNDED_TEE.search(line):
            rule, severity = "unbounded-tee-output", "medium"
        elif UNBOUNDED_DIFF.search(line) and not SAFE_DIFF.search(line):
            rule, severity = "unbounded-git-diff-output", "medium"
        else:
            match = TAIL_COUNT.search(line)
            if match and int(match.group(1)) > 35:
                rule, severity = "oversized-tail", "medium"
        if rule:
            findings.append({
                "file": path[:160],
                "line": index,
                "rule": rule,
                "severity": severity,
            })
    return findings


def bounded_report(data: dict, budget: int = REPORT_BYTES) -> bytes:
    """Produce valid JSON, never split a UTF-8 sequence or exceed budget."""
    payload = dict(data)
    findings = list(payload.get("findings", []))
    payload["findings"] = findings
    payload["truncated_findings"] = 0
    encode = lambda obj: (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    result = encode(payload)
    while len(result) > budget and findings:
        findings.pop()
        payload["truncated_findings"] += 1
        result = encode(payload)
    if len(result) > budget:
        raise ValueError("Audit summary alone exceeds report byte budget")
    return result


class Github:
    def __init__(self, repo: str, token: str = ""):
        if not REPO_PATTERN.fullmatch(repo):
            raise ValueError("Expected owner/repo")
        self.repo = repo
        self.token = token
        self.calls = 0

    def get(self, path: str):
        if not path.startswith("/repos/" + self.repo + "/") and path != "/repos/" + self.repo:
            raise ValueError("GitHub API path must stay inside the requested repository")
        req = Request("https://api.github.com" + path, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Seamless-Hunt-Bounded-CI-Audit",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": "Bearer " + self.token} if self.token else {}),
        })
        try:
            with urlopen(req, timeout=18) as response:
                raw = response.read(API_BYTES + 1)
        except (HTTPError, URLError) as exc:
            # No error body, token, request headers or arbitrary remote text.
            status = getattr(exc, "code", None)
            raise RuntimeError("GitHub API request failed (HTTP %s)" % (status or "network")) from None
        if len(raw) > API_BYTES:
            raise ValueError("GitHub response exceeds 1 MiB; refuse unbounded input")
        self.calls += 1
        return json.loads(raw)


def audit_open_prs(api: Github, max_prs: int = 100, max_files: int = 250) -> dict:
    prs = []
    for page in range(1, 6):
        chunk = api.get("/repos/" + api.repo + "/pulls?state=open&per_page=30&page=" + str(page))
        prs += chunk
        if len(chunk) < 30 or len(prs) >= max_prs:
            break
    incomplete = len(prs) > max_prs or (len(prs) == 150)
    prs = prs[:max_prs]
    # Always include default branch too; old and new PR branches are both covered.
    repo = api.get("/repos/" + api.repo)
    refs = [("default:" + repo["default_branch"], repo["default_branch"])]
    refs.extend(("#" + str(x["number"]), x["head"]["sha"]) for x in prs)
    cached: dict[str, list[dict]] = {}
    findings = []
    skipped = []
    inspected = 0
    for label, ref in refs:
        if len(refs) > 110:
            incomplete = True
        try:
            items = api.get("/repos/" + api.repo + "/contents/.github/workflows?ref=" + quote(ref, safe=""))
        except (RuntimeError, ValueError):
            skipped.append({"ref": label[:50], "reason": "workflow-directory-unavailable"})
            incomplete = True
            continue
        if not isinstance(items, list) or len(items) > 80:
            skipped.append({"ref": label[:50], "reason": "unexpected-workflow-list"})
            incomplete = True
            continue
        for item in items:
            path = item.get("path", "")
            if item.get("type") != "file" or not path.endswith(WORKFLOW_SUFFIX):
                continue
            size = item.get("size", 0)
            if not isinstance(size, int) or size > WORKFLOW_BYTES:
                skipped.append({"ref": label[:50], "reason": "workflow-over-64KiB", "file": path[:150]})
                incomplete = True
                continue
            sha = item.get("sha", "")
            if not re.fullmatch(r"[0-9a-f]{40}", sha):
                incomplete = True
                continue
            if sha not in cached:
                if len(cached) >= max_files:
                    incomplete = True
                    skipped.append({"ref": label[:50], "reason": "unique-workflow-budget-exhausted"})
                    break
                try:
                    result = api.get("/repos/" + api.repo + "/contents/" + quote(path, safe="/") + "?ref=" + quote(ref, safe=""))
                    if result.get("encoding") != "base64":
                        raise ValueError("Unexpected GitHub file encoding")
                    raw = base64.b64decode(result["content"], validate=False)
                    if len(raw) > WORKFLOW_BYTES or result.get("sha") != sha:
                        raise ValueError("GitHub blob mismatch or oversized file")
                    cached[sha] = scan_workflow(path, raw.decode("utf-8"))
                    inspected += 1
                except (RuntimeError, ValueError, UnicodeError, KeyError):
                    incomplete = True
                    skipped.append({"ref": label[:50], "reason": "workflow-unreadable", "file": path[:150]})
                    continue
            findings.extend({"ref": label, **risk} for risk in cached[sha])
    high = sum(x["severity"] in ("critical", "high") for x in findings)
    return {
        "kind": "open-pr-workflow-audit", "repo": api.repo,
        "prs_examined": len(prs), "refs_examined": len(refs),
        "unique_workflows_examined": inspected, "github_requests": api.calls,
        "findings_count": len(findings), "high_or_critical_count": high,
        "incomplete": incomplete, "skipped_count": len(skipped),
        "skipped_examples": skipped[:8], "findings": findings,
    }


def inspect_run(api: Github, run_id: int) -> dict:
    """Only run/job/step metadata. NEVER fetch workflow job or run logs."""
    root = "/repos/" + api.repo + "/actions/runs/" + str(run_id)
    data = api.get(root)
    results = []
    incomplete = False
    for page in range(1, 6):
        jobs = api.get(root + "/jobs?per_page=20&page=" + str(page))
        for job in jobs.get("jobs", []):
            problems = [
                {"name": s.get("name", "")[:120], "conclusion": s.get("conclusion")}
                for s in job.get("steps", [])
                if s.get("conclusion") in ("failure", "timed_out", "cancelled")
            ]
            results.append({
                "name": job.get("name", "")[:130],
                "id": job.get("id"), "status": job.get("status"),
                "conclusion": job.get("conclusion"), "failed_steps": problems[:8],
            })
        if len(jobs.get("jobs", [])) < 20:
            break
    else:
        incomplete = True
    return {
        "kind": "metadata-only-run", "repo": api.repo, "run_id": run_id,
        "status": data.get("status"), "conclusion": data.get("conclusion"),
        "head_sha": data.get("head_sha"), "incomplete": incomplete,
        "jobs_count": len(results), "findings": results,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan-local")
    scan.add_argument("--directory", type=Path, default=Path(".github/workflows"))
    audit = sub.add_parser("audit-open-prs")
    audit.add_argument("--repo", required=True)
    audit.add_argument("--max-prs", type=int, default=100)
    audit.add_argument("--max-files", type=int, default=250)
    inspect = sub.add_parser("inspect-run")
    inspect.add_argument("--repo", required=True)
    inspect.add_argument("--run-id", type=int, required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    try:
        if a.command == "scan-local":
            files = sorted(x for x in a.directory.iterdir() if x.suffix in WORKFLOW_SUFFIX)
            findings = []
            for file in files:
                if file.stat().st_size > WORKFLOW_BYTES:
                    raise ValueError("Workflow exceeds 64KiB: " + file.name)
                findings.extend(scan_workflow(file.name, file.read_text(encoding="utf-8")))
            result = {"kind": "local-workflow-audit", "files_examined": len(files),
                      "findings_count": len(findings), "incomplete": False, "findings": findings}
        else:
            api = Github(a.repo, os.environ.get("GITHUB_TOKEN", ""))
            if a.command == "audit-open-prs":
                if not (1 <= a.max_prs <= 150 and 1 <= a.max_files <= 500):
                    raise ValueError("Invalid audit bounds")
                result = audit_open_prs(api, a.max_prs, a.max_files)
            else:
                if a.run_id < 1:
                    raise ValueError("Invalid run ID")
                result = inspect_run(api, a.run_id)
        wire = bounded_report(result)
        if a.output:
            a.output.parent.mkdir(parents=True, exist_ok=True)
            a.output.write_bytes(wire)
        sys.stdout.buffer.write(wire)
        return 2 if result.get("incomplete") else 0
    except (RuntimeError, ValueError, OSError, UnicodeError) as exc:
        sys.stderr.write("CI_OUTPUT_GUARD_ERROR: " + str(exc)[:180] + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
