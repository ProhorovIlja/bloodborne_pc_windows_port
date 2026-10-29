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
                         "droogie/bbhost", "Mrsuss60/bloodborne_pc_windows_port",
                         "Awakenchan/LanternEngine", "DarkIzuku/bloodborne_pc",
                         "Wozzardman/shadnet-p2p"}.issubset(names))
        self.assertGreaterEqual(len(names), 12)
        self.assertGreaterEqual(len(self.data["pull_requests"]), 61)
        self.assertIn(("Jgamrot/yharnam-pc", 219),
                      {(p["repo"], p["number"]) for p in self.data["pull_requests"]})
        self.assertIn(("Jgamrot/yharnam-pc", 179),
                      {(p["repo"], p["number"]) for p in self.data["pull_requests"]})
        self.assertIn(("Jgamrot/yharnam-pc", 198),
                      {(p["repo"], p["number"]) for p in self.data["pull_requests"]})
        self.assertIn("Jgamrot/yharnam-pc", names)
        self.assertIn(("Jgamrot/yharnam-pc", 77),
                      {(p["repo"], p["number"]) for p in self.data["pull_requests"]})
        self.assertGreaterEqual(len(self.data["branches"]), 8)
        self.assertIn(("Awakenchan/LanternEngine", "online-shadps4-0.20"),
                      {(x["repo"], x["branch"]) for x in self.data["branches"]})
        # Comparing engines is allowed; the native YT auth/wire is never replaced.
        for name in ("Awakenchan/LanternEngine", "Wozzardman/shadnet-p2p"):
            entry = next(r for r in self.data["repositories"] if r["full_name"] == name)
            self.assertIn("NO_YT", entry["compatibility"])

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

    def test_rejects_unsafe_branch_names_and_missing_sha(self):
        cases = ("../secrets", "/oops", "x//y", "branch?token=yes", "-bad")
        for name in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                data = json.loads(json.dumps(self.data))
                data["branches"][0]["branch"] = name
                p = Path(tmp) / "bad.json"
                p.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    m.load_inventory(p)
        with tempfile.TemporaryDirectory() as tmp:
            data = json.loads(json.dumps(self.data))
            data["branches"][0]["known_head"] = "main"
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                m.load_inventory(p)
            data = json.loads(json.dumps(self.data))
            data["branches"][0]["repo"] = "attacker/unknown"
            p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                m.load_inventory(p)

    def test_reports_release_head_and_merged_pr_drift(self):
        observed = {}
        for row in self.data["repositories"]:
            name = row["full_name"]
            observed["/repos/" + name + "/commits/HEAD"] = {"sha": row["known_head"]}
            observed["/repos/" + name + "/releases/latest"] = {
                "tag_name": row["known_release_tag"]}
        for row in self.data["branches"]:
            observed["/repos/" + row["repo"] + "/branches/" + row["branch"]] = {
                "name": row["branch"], "commit": {"sha": row["known_head"]}}
        first_branch = self.data["branches"][0]
        observed["/repos/" + first_branch["repo"] + "/branches/" +
                 first_branch["branch"]] = {"commit": {"sha": "d" * 40}}
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
        self.assertTrue(report["branches"][0]["head_changed"])
        self.assertIn("## Selected active and historical branches", m.markdown(report))
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
            if "/branches/" in path:
                raise ValueError("missing branch")
            return {"sha": "b" * 40}
        report = m.survey(self.data, failing)
        self.assertEqual(len(report["errors"]), len(self.data["repositories"]) +
                         len(self.data["branches"]) + len(self.data["pull_requests"]))
        self.assertTrue(all(not b["evidence_complete"] for b in report["branches"]))
        self.assertTrue(all(not x["evidence_complete"] for x in report["repositories"]))
        self.assertTrue(all(not x["state_changed"] for x in report["pull_requests"]))
        self.assertNotIn("Bearer", json.dumps(report))

    def test_branch_missing_or_broken_metadata_is_unknown_not_no_change(self):
        def get(path):
            if "/branches/" in path:
                return {"name": "not-valid", "commit": {"sha": []}}
            if "/pulls/" in path:
                return {"state": "open"}
            if "/releases/" in path:
                return {"tag_name": "unverified"}
            return {"sha": "f" * 40}
        report = m.survey(self.data, get)
        self.assertTrue(all(not b["evidence_complete"] for b in report["branches"]))
        self.assertTrue(all(not b["head_changed"] for b in report["branches"]))
        self.assertEqual(len(report["errors"]), 0)
        self.assertIn("UNKNOWN", m.markdown(report))

    def test_open_pr_new_commit_is_reviewed_even_without_state_change(self):
        tracked = next(p for p in self.data["pull_requests"]
                       if p["repo"] == "ProhorovIlja/bloodborne_pc_windows_port"
                       and p["number"] == 37)
        self.assertEqual(len(tracked["last_seen_head"]), 40)

        def get(path):
            if path.endswith("/pulls/37") and "ProhorovIlja" in path:
                return {"state": "open", "merged_at": None,
                        "head": {"sha": "a" * 40}}
            if "/pulls/" in path:
                return {"state": "open", "merged_at": None}
            if "/branches/" in path:
                return {"commit": {"sha": "b" * 40}}
            if "/releases/latest" in path:
                return {"tag_name": "unverified"}
            return {"sha": "c" * 40}

        report = m.survey(self.data, get)
        pr = next(x for x in report["pull_requests"]
                  if x["repo"] == tracked["repo"] and x["number"] == 37)
        self.assertFalse(pr["state_changed"])
        self.assertTrue(pr["head_changed"])
        self.assertTrue(pr["head_evidence_complete"])
        self.assertIn("HEAD UPDATED: REVIEW", m.markdown(report))

        missing = {**tracked, "last_seen_head": "not-a-sha"}
        with tempfile.TemporaryDirectory() as tmp:
            data = json.loads(json.dumps(self.data))
            for index, row in enumerate(data["pull_requests"]):
                if row["repo"] == missing["repo"] and row["number"] == missing["number"]:
                    data["pull_requests"][index] = missing
                    break
            source = Path(tmp) / "bad-head.json"
            source.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "Unpinned reviewed PR"):
                m.load_inventory(source)

    def test_fetch_refuses_arbitrary_urls_and_unsafe_paths(self):
        for path in ("https://evil.invalid/", "/users/oai", "/repos/a/b/../secrets",
                     "/repos/a/b?token=x"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    m.fetch(path)


if __name__ == "__main__":
    unittest.main()
