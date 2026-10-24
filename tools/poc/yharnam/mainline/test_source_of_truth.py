"""Regression tests for one Yharnam Together client+launcher+server mainline."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).with_name("check_source_of_truth.py")
spec = importlib.util.spec_from_file_location("sh_mainline_source_policy", SCRIPT)
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)


class MainlineContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = json.loads(p.POLICY.read_text(encoding="utf-8"))

    def test_real_repository_and_merged_workflows(self):
        p.check_workspace(p.REPO_ROOT, self.good)

    def test_v1_2_cannot_enter_without_pinned_review(self):
        changed = copy.deepcopy(self.good)
        changed["source_of_truth"]["commit"] = changed["source_of_truth"]["newer_upstream_review"]["commit"]
        with self.assertRaisesRegex(p.SourceDrift, "pinned"):
            p.check_policy(changed)

    def test_old_launchers_and_emulated_game_builds_rejected(self):
        for field, bad in [("upstream", "launcher.py"),
                           ("coop", "launcher/bbsc.py")]:
            with self.subTest(field=field):
                changed = copy.deepcopy(self.good)
                changed["components"]["launcher"][field] = bad
                with self.assertRaises(p.SourceDrift):
                    p.check_policy(changed)
        changed = copy.deepcopy(self.good)
        changed["components"]["game"]["build"] = "build.bat"
        with self.assertRaises(p.SourceDrift):
            p.check_policy(changed)

    def test_debian_and_unapproved_release_rejected(self):
        altered = copy.deepcopy(self.good)
        altered["components"]["server"]["linux"]["os"] = "Debian 12"
        with self.assertRaises(p.SourceDrift):
            p.check_policy(altered)
        for flag in ("release_ready", "fornex_deployment_authorized"):
            altered = copy.deepcopy(self.good)
            altered[flag] = True
            with self.assertRaises(p.SourceDrift):
                p.check_policy(altered)

    def test_unverified_gameplay_not_silently_certified(self):
        altered = copy.deepcopy(self.good)
        altered["feature_status"]["not_yet_game_verified"].remove("npc_summon_signs")
        with self.assertRaisesRegex(p.SourceDrift, "npc_summon_signs"):
            p.check_policy(altered)

    def test_qt_http_server_gplv3_cannot_be_mislabelled_lgpl(self):
        altered = copy.deepcopy(self.good)
        altered["attribution_and_licenses"]["qt_httpserver_6_8_3_open_source_license"] = "LGPL-3.0"
        with self.assertRaisesRegex(p.SourceDrift, "GPL"):
            p.check_policy(altered)

    def test_no_distribution_without_complete_license_audit(self):
        for key in ("redistribution_approved", "release_license_audit_completed"):
            altered = copy.deepcopy(self.good)
            altered["attribution_and_licenses"][key] = True
            with self.subTest(key=key), self.assertRaises(p.SourceDrift):
                p.check_policy(altered)

    def test_downstream_author_and_upstream_license_docs_required(self):
        for name in ("README.md", "CREDITS.md", "THIRD_PARTY_NOTICES.md"):
            altered = copy.deepcopy(self.good)
            altered["attribution_and_licenses"]["english_docs"].remove(name)
            with self.subTest(name=name), self.assertRaises(p.SourceDrift):
                p.check_policy(altered)

    def test_protocols_never_implicitly_crossplay(self):
        original = json.loads(p.POLICY.with_name("interop_policy.json").read_text("utf-8"))
        p.check_interop_policy(original)
        for index in range(4):
            modified = copy.deepcopy(original)
            modified["providers"][index]["crossplay_with_cls_verified"] = True
            with self.subTest(index=index), self.assertRaisesRegex(p.SourceDrift, "cross-client"):
                p.check_interop_policy(modified)

    def test_no_forced_player_move_or_credentials_or_save_rewrites(self):
        original = json.loads(p.POLICY.with_name("interop_policy.json").read_text("utf-8"))
        for key in ("force_user_migration", "replace_live_fornex",
                    "auto_forward_player_credentials",
                    "allow_cross_protocol_join_without_live_tests"):
            modified = copy.deepcopy(original)
            modified[key] = True
            with self.subTest(key=key), self.assertRaisesRegex(p.SourceDrift, "Unsafe"):
                p.check_interop_policy(modified)
        modified = copy.deepcopy(original)
        modified["preserve_existing_saves"] = False
        with self.assertRaisesRegex(p.SourceDrift, "saves"):
            p.check_interop_policy(modified)

    def test_nightwatch_visy_and_cls_are_research_not_shipped(self):
        original = json.loads(p.POLICY.with_name("interop_policy.json").read_text("utf-8"))
        for index in range(1, 4):
            modified = copy.deepcopy(original)
            modified["providers"][index]["included"] = True
            with self.subTest(index=index), self.assertRaisesRegex(p.SourceDrift, "Research-only"):
                p.check_interop_policy(modified)

    def test_cannot_drop_client_host_server_or_event_check(self):
        for name in list(self.good["mainline_workflows"]):
            altered = copy.deepcopy(self.good)
            del altered["mainline_workflows"][name]
            with self.subTest(name=name), self.assertRaises(p.SourceDrift):
                p.check_policy(altered)


if __name__ == "__main__":
    unittest.main()
