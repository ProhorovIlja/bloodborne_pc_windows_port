"""Offline contract tests for the read-only cross-fork watchdog."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).with_name("watch.py")
SPEC = importlib.util.spec_from_file_location("bb_upstream_watch", MODULE)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class SourceWatchTests(unittest.TestCase):
    def setUp(self):
        self.data = m.load_inventory()

    def test_repository_and_pull_request_registry_contracts(self):
        self.assertGreaterEqual(len(self.data["repositories"]), 6)
        self.assertGreaterEqual(len(self.data["pull_requests"]), 15)
        self.assertEqual(self.data["policy"], "REPORT_ONLY_NEVER_AUTOMATICALLY_IMPORT_OR_DEPLOY")
        names = {r["full_name"] for r in self.data["repositories"]}
        self.assertTrue({"lKaniel/bloodborne-server", "visy/bloodborne_pc_windows_port",
                         "Supermedo/bloodborne_pc", "deadinside28/bloodborne_pc",
                         "droogie/bbhost", "Mrsuss60/bloodborne_pc_windows_port"}.issubset(names))

    def test_fails_closed_if_repo_injected_or_pinning_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = json.loads(json.dumps(self.data))
            data["repositories"][0]["full_name"] = "../broken/evil"
            file = Path(tmp) / "broken.json"
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                m.load_inventory(file)
            data = json.loads(json.dumps(self.data))
            data["repositories"][0]["known_head"] = "master"
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                m.load_inventory(file)
            data = json.loads(json.dumps(self.data))
            data["policy"] = "AUTO_DEPLOY"
            file.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                m.load_inventory(file)

    def test_reports_release_head_and_merged_pr_drift(self):
        observed = {}
        for row in self.data["repositories"]:
            name = row["full_name"]
            observed["/repos/" + name + "/commits/HEAD"] = {"sha": row["known_head"]}
            observed["/repos/" + name + "/releases/latest"] = {
                "tag_name": row["known_release_tag"]}
        for row in self.data["pull_requests"]:
            endpoint = "/repos/" + row["repo"] + "/pulls/" + str(row["number"])
            observed[endpoint] = {
                "state": "open" if row["last_seen"] == "open" else "closed",
                "merged_at": "2026-10-27T12:00:00Z" if row["last_seen"] == "merged" else None,
                "merge_commit_sha": "f" * 40,
            }
        first = self.data["repositories"][0]["full_name"]
        observed["/repos/" + first + "/commits/HEAD"] = {"sha": "e" * 40}
        observed["/repos/" + first + "/releases/latest"] = {"tag_name": "v1.3.1"}
        observed["/repos/lKaniel/bloodborne-server/pulls/423"] = {
            "state": "closed", "merged_at": "2026-10-27T14:00:00Z",
            "merge_commit_sha": "a" * 40,
        }
        report = m.survey(self.data, observed.__getitem__)
        self.assertTrue(report["repositories"][0]["head_changed"])
        self.assertTrue(report["repositories"][0]["release_changed"])
        pr = next(p for p in report["pull_requests"] if p["number"] == 423)
        self.assertTrue(pr["state_changed"])
        self.assertEqual(pr["observed_state"], "merged")
        self.assertEqual(pr["merge_commit"], "a" * 40)
        self.assertIn("REVIEW REQUIRED", m.markdown(report))
        self.assertIn("Never change Fornex/CLS Friends", m.markdown(report))
        self.assertEqual(report["errors"], [])

    def test_rate_limit_or_missing_release_is_unknown_not_green(self):
        def failing(path):
            if "/releases/latest" in path:
                raise OSError("rate limited / not published")
            if "/pulls/" in path:
                raise ValueError("missing PR")
            return {"sha": "b" * 40}
        report = m.survey(self.data, failing)
        self.assertEqual(len(report["errors"]), len(self.data["repositories"]) +
                         len(self.data["pull_requests"]))
        self.assertTrue(all(not x["evidence_complete"] for x in report["repositories"]))
        self.assertTrue(all(not x["state_changed"] for x in report["pull_requests"]))
        self.assertNotIn("Bearer", json.dumps(report))

    def test_fetch_refuses_arbitrary_urls_and_unsafe_paths(self):
        for path in ("https://evil.invalid/", "/users/oai", "/repos/a/b/../secrets",
                     "/repos/a/b?token=x"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    m.fetch(path)


if __name__ == "__main__":
    unittest.main()
