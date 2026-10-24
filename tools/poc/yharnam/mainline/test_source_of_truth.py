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

    def test_reusable_native_jobs_are_connected_from_canonical_mainline(self):
        meta = self.good
        workflows = {
            key: (p.REPO_ROOT / relative).read_text("utf-8")
            for key, relative in meta["mainline_workflows"].items()
        }
        orchestrator = (p.REPO_ROOT / ".github/workflows/shyt-mainline-candidate.yml").read_text("utf-8")
        # Deliberately branch-agnostic reusable jobs are accepted through their
        # canonical caller, not because they happen to contain a branch string.
        p.check_workflow_wiring(meta, workflows, orchestrator)
        self.assertNotIn(p.CANONICAL, workflows["windows_game"])

        with self.assertRaisesRegex(p.SourceDrift, "entry point"):
            p.check_workflow_wiring(meta, workflows, orchestrator.replace(
                f"branches: [{p.CANONICAL}]", "branches: [master]"))
        with self.assertRaisesRegex(p.SourceDrift, "disconnected"):
            p.check_workflow_wiring(meta, workflows, orchestrator.replace(
                f"uses: ./{meta['mainline_workflows']['windows_game']}",
                "uses: ./.github/workflows/legacy-client.yml"))
        without_pin = dict(workflows)
        without_pin["linux_server"] = without_pin["linux_server"].replace(p.PIN, "0" * 40)
        with self.assertRaisesRegex(p.SourceDrift, "pins"):
            p.check_workflow_wiring(meta, without_pin, orchestrator)
        with self.assertRaisesRegex(p.SourceDrift, "event/kit"):
            p.check_workflow_wiring(meta, workflows, orchestrator.replace(
                "test_patch_windows_package.py", "skipped_package_test.py"))
        with self.assertRaisesRegex(p.SourceDrift, "assemble before"):
            p.check_workflow_wiring(meta, workflows, orchestrator.replace(
                "needs: [windows-game, windows-coop-host, fornex-ubuntu-staging]",
                "needs: windows-game"))

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

    def test_current_server_relay_is_not_misrepresented_as_direct_p2p(self):
        config = json.loads(p.POLICY.with_name(
            "transport_and_feature_priorities.json").read_text("utf-8"))
        p.check_transport_feature_policy(config)
        for field, wrong in (("mode", "direct_p2p"),
                             ("client_peer_direct_game_packets", True),
                             ("server_memory_and_egress_measured", True)):
            changed = copy.deepcopy(config)
            changed["current_transport"][field] = wrong
            with self.subTest(field=field), self.assertRaisesRegex(p.SourceDrift, "P2P|load"):
                p.check_transport_feature_policy(changed)

    def test_direct_p2p_prototype_requires_consent_and_real_network_data(self):
        config = json.loads(p.POLICY.with_name(
            "transport_and_feature_priorities.json").read_text("utf-8"))
        for field in ("must_not_auto_enable",
                      "require_consent_for_network_endpoint_exposure",
                      "never_forward_account_password_or_auth_token_to_peers"):
            changed = copy.deepcopy(config)
            changed["target_transport"][field] = False
            with self.subTest(field=field), self.assertRaises(p.SourceDrift):
                p.check_transport_feature_policy(changed)
        changed = copy.deepcopy(config)
        changed["benchmarks"]["verified_live_p2p"] = True
        with self.assertRaisesRegex(p.SourceDrift, "measured"):
            p.check_transport_feature_policy(changed)

    def test_friends_are_a_real_api_but_not_an_unverified_in_game_feature(self):
        policy = json.loads(p.POLICY.with_name(
            "transport_and_feature_priorities.json").read_text("utf-8"))
        p.check_transport_feature_policy(policy)
        for field in ("in_game_friend_ui_status", "invasion_ui_status"):
            changed = copy.deepcopy(policy)
            changed["friend_list"][field] = "fully_game_verified"
            with self.subTest(field=field), self.assertRaisesRegex(p.SourceDrift, "friend"):
                p.check_transport_feature_policy(changed)
        changed = copy.deepcopy(policy)
        changed["friend_list"]["enforcement"].remove(
            "no password bypass or private session lookup by guessed ID")
        with self.assertRaisesRegex(p.SourceDrift, "Friends/privacy"):
            p.check_transport_feature_policy(changed)
        changed = copy.deepcopy(policy)
        changed["priority_order"][1]["features"].remove(
            "friend_invite_and_authorized_join")
        with self.assertRaisesRegex(p.SourceDrift, "Friends UX"):
            p.check_transport_feature_policy(changed)

    def test_souls_features_cannot_bypass_core_client_and_save_requirements(self):
        config = json.loads(p.POLICY.with_name(
            "transport_and_feature_priorities.json").read_text("utf-8"))
        changed = copy.deepcopy(config)
        changed["priority_order"][0]["features"].remove("safe_save_backups")
        with self.assertRaisesRegex(p.SourceDrift, "safe_save_backups"):
            p.check_transport_feature_policy(changed)
        changed = copy.deepcopy(config)
        changed["priority_order"][0]["priority"] = 2
        with self.assertRaisesRegex(p.SourceDrift, "P0"):
            p.check_transport_feature_policy(changed)
        changed = copy.deepcopy(config)
        changed["design_references"][0]["status"] = "source_code_imported"
        with self.assertRaisesRegex(p.SourceDrift, "inspiration"):
            p.check_transport_feature_policy(changed)

    def test_invasions_are_a_core_goal_but_never_forced_on_pve_parties(self):
        policy = json.loads(p.POLICY.with_name(
            "transport_and_feature_priorities.json").read_text("utf-8"))
        p.check_transport_feature_policy(policy)
        change = copy.deepcopy(policy)
        change["invasion_policy"]["enabled_by_default"] = True
        with self.assertRaisesRegex(p.SourceDrift, "invasion"):
            p.check_transport_feature_policy(change)
        change = copy.deepcopy(policy)
        change["priority_order"][0]["features"].remove("opt_in_invasions")
        with self.assertRaisesRegex(p.SourceDrift, "opt_in_invasions"):
            p.check_transport_feature_policy(change)

    def test_cannot_drop_client_host_server_or_event_check(self):
        for name in list(self.good["mainline_workflows"]):
            altered = copy.deepcopy(self.good)
            del altered["mainline_workflows"][name]
            with self.subTest(name=name), self.assertRaises(p.SourceDrift):
                p.check_policy(altered)


if __name__ == "__main__":
    unittest.main()
