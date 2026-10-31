#!/usr/bin/env python3
"""Offline tests: no network, game binaries, credentials or log archives."""
import base64
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ci_output_guard import (
    Github, audit_open_prs, bounded_report, inspect_run, scan_workflow,
)


class FakeGithub:
    repo = "example/native-port"

    def __init__(self):
        self.calls = 0
        self.requested = []

    def get(self, path):
        self.calls += 1
        self.requested.append(path)
        if "/logs" in path:
            raise AssertionError("A raw log endpoint was requested!")
        if "/pulls?" in path:
            return [{"number": 73, "head": {"sha": "f" * 40}}]
        if path == "/repos/example/native-port":
            return {"default_branch": "master"}
        if "/contents/.github/workflows?" in path:
            return [{"path": ".github/workflows/one.yml", "name": "one.yml",
                     "sha": "a" * 40, "size": 41, "type": "file"}]
        if "/contents/.github/workflows/one.yml?" in path:
            raw = b"name: CI\njobs:\n  test:\n    run: cat job.log\n"
            return {"content": base64.b64encode(raw).decode(),
                    "sha": "a" * 40, "encoding": "base64"}
        if path.endswith("/actions/runs/123"):
            return {"status": "completed", "conclusion": "failure", "head_sha": "1" * 40}
        if "/actions/runs/123/jobs?" in path:
            return {"jobs": [
                {"name": "Windows compiler", "id": 8, "status": "completed",
                 "conclusion": "failure",
                 "steps": [{"name": "Compile", "conclusion": "success"},
                           {"name": "Diff guard", "conclusion": "failure"}]}
            ]}
        raise AssertionError("Unexpected API URL " + path)


class OutputGuardTests(unittest.TestCase):
    def test_high_risk_raw_log_fetch(self):
        findings = scan_workflow("ci.yml", "run: fetch_workflow_job_logs(repo, job)\n")
        self.assertEqual(findings[0]["severity"], "critical")
        self.assertEqual(findings[0]["rule"], "raw-actions-log-download")

    def test_bounded_log_is_not_flagged(self):
        self.assertEqual(scan_workflow("ci.yml", "run: head -c 6000 diagnostic.log\n"), [])

    def test_unbounded_cat_and_tee(self):
        findings = scan_workflow("ci.yml", "run: cat compile.log\n  tee massive.log\n")
        self.assertEqual([x["rule"] for x in findings],
                         ["unbounded-log-dump", "unbounded-tee-output"])

    def test_large_tail_only(self):
        self.assertFalse(scan_workflow("ci.yml", "run: tail -n 20 compiler.log\n"))
        self.assertEqual(scan_workflow("ci.yml", "run: tail -n 100 compiler.log\n")[0]["rule"],
                         "oversized-tail")

    def test_git_diff_guard_is_safe(self):
        self.assertFalse(scan_workflow("ci.yml", "run: git -C source diff --check\n"))
        self.assertEqual(scan_workflow("ci.yml", "run: git diff\n")[0]["rule"],
                         "unbounded-git-diff-output")

    def test_untrusted_content_never_appears_in_report(self):
        source = "run: cat secret-ABCDE123.log\n"
        finding = scan_workflow("ci.yml", source)
        wire = bounded_report({"findings": finding, "findings_count": 1}, 4000)
        self.assertNotIn(b"secret-ABCDE123", wire)
        self.assertNotIn(b"cat ", wire)

    def test_utf8_report_is_valid_and_strictly_bounded(self):
        findings = [{"file": "shyt-" + str(i) + ".yml", "severity": "high",
                     "rule": "unbounded-log-dump", "line": i}
                    for i in range(600)]
        wire = bounded_report({"kind": "test", "findings_count": len(findings),
                               "findings": findings}, 1024)
        import json
        result = json.loads(wire)
        self.assertLessEqual(len(wire), 1024)
        self.assertGreater(result["truncated_findings"], 0)
        self.assertEqual(result["findings_count"], 600)

    def test_open_pr_audit_deduplicates_identical_blobs(self):
        api = FakeGithub()
        result = audit_open_prs(api)
        self.assertEqual(result["prs_examined"], 1)
        self.assertEqual(result["refs_examined"], 2)
        self.assertEqual(result["unique_workflows_examined"], 1)
        self.assertEqual(result["findings_count"], 2)
        self.assertEqual(result["high_or_critical_count"], 2)
        self.assertFalse(result["incomplete"])
        self.assertFalse(any("/logs" in p for p in api.requested))

    def test_inspect_run_uses_only_metadata_and_failed_steps(self):
        api = FakeGithub()
        result = inspect_run(api, 123)
        self.assertEqual(result["conclusion"], "failure")
        self.assertEqual(result["findings"][0]["failed_steps"],
                         [{"name": "Diff guard", "conclusion": "failure"}])
        self.assertFalse(any("/logs" in p for p in api.requested))

    def test_repo_validation_blocks_external_api_targets(self):
        with self.assertRaises(ValueError):
            Github("../other")
        with self.assertRaises(ValueError):
            Github("example/native-port").get("/repos/other/private/actions/runs/1")


if __name__ == "__main__":
    unittest.main()
