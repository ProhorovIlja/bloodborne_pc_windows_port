#!/usr/bin/env python3
"""Mainline provenance gate: native Yharnam Together, never the old master port.

This is an executable DEVELOPMENT-GUARD, not a declaration of gameplay success.
Version upgrade, relay credentials, legacy matchmaking and real save tests remain
release blockers. Do not weaken this to accept unpinned upstream sources.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
POLICY = Path(__file__).with_name("source_of_truth.json")
PIN = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"
CANONICAL = "feature/seamless-hunt-mainline"

class SourceDrift(ValueError):
    pass


def check_interop_policy(policy: dict) -> None:
    # Seamless Hunt's only supported multiplayer runtime is Yharnam Together.
    # Researching another author's optimization is NOT permission to silently
    # adopt a foreign account system or speak another game's wire protocol.
    if (policy.get("schema") != 1
            or policy.get("default_client") != "yharnam_together"
            or policy.get("default_server") != "experimental_yt_shadnet"
            or policy.get("default_version") != PIN
            or policy.get("supported_game_protocol") != "yharnam_together_only"
            or policy.get("supported_network_clients") != ["yharnam_together"]
            or policy.get("third_party_crossplay_enabled") is not False
            or policy.get("external_projects_ideas_only") is not True):
        raise SourceDrift("Only original Yharnam Together multiplayer protocol is supported")
    for key in ("force_user_migration", "replace_live_fornex",
                "auto_forward_player_credentials",
                "allow_cross_protocol_join_without_live_tests"):
        if policy.get(key) is not False:
            raise SourceDrift("Unsafe cross-provider migration toggle: " + key)
    if policy.get("preserve_existing_saves") is not True:
        raise SourceDrift("Cannot permit migration that overwrites player saves")
    providers = policy.get("providers")
    if not isinstance(providers, list) or len(providers) != 1:
        raise SourceDrift("Additional online clients are forbidden in Seamless Hunt")
    only = providers[0]
    if (not isinstance(only, dict) or only.get("id") != "yharnam_together"
            or only.get("project") != "lKaniel/bloodborne-server"
            or only.get("source") != "https://github.com/lKaniel/bloodborne-server"
            or only.get("included") is not True
            or only.get("crossplay_with_cls_verified") is not False):
        raise SourceDrift("Yharnam Together must be the only multiplayer client")
    essentials = {"pinned_provenance", "account_and_save_backup",
                  "explicit_player_opt_in", "two_real_pc_gameplay_logs",
                  "negative_password_isolation_tests",
                  "same_version_game_and_server_protocol",
                  "direct_p2p_and_relay_fallback_2pc_tests"}
    if not essentials.issubset(set(policy.get("transitions_require", []))):
        raise SourceDrift("Cannot skip same-protocol gameplay and network release tests")


def check_transport_feature_policy(policy: dict) -> None:
    # The pinned Yharnam Together team runtime currently uses one UDP link
    # per client and relays game frames through the server. The old P2P
    # description in NATIVE_NETCODE.md predates SERVER_COOP_PLAN.md.
    if (policy.get("schema") != 1
            or policy.get("source") != "lKaniel/bloodborne-server"
            or policy.get("source_commit") != PIN
            or policy.get("documented_source") != "docs/SERVER_COOP_PLAN.md"):
        raise SourceDrift("network transport policy no longer matches pinned upstream")
    current = policy.get("current_transport", {})
    if (current.get("mode") != "server_relay_udp"
            or current.get("client_peer_direct_game_packets") is not False
            or current.get("central_server_owns_shared_world") is not True
            or current.get("game_net_packets_forwarded_by_shadnet") is not True
            or current.get("server_memory_and_egress_measured") is not False):
        raise SourceDrift("cannot advertise untested direct P2P or server load figures")
    target = policy.get("target_transport", {})
    if (target.get("mode") != "hybrid_direct_p2p_with_relay_fallback"
            or target.get("status") != "design_only_not_implemented"
            or target.get("must_not_auto_enable") is not True
            or target.get("require_consent_for_network_endpoint_exposure") is not True
            or target.get("never_forward_account_password_or_auth_token_to_peers") is not True):
        raise SourceDrift("experimental direct P2P must be opt-in and protect credentials")
    benchmarks = policy.get("benchmarks", {})
    if (benchmarks.get("verified_live_p2p") is not False
            or benchmarks.get("verified_fornex_relay_load") is not False):
        raise SourceDrift("cannot mark P2P or production bandwidth measured without a real test")
    required = {"two_clients_one_host", "guest_door_interaction", "npc_summon_sign",
                "optional_invasion", "host_disconnect_recovery", "two_hour_soak",
                "bad_network_packet_loss_and_jitter"}
    if not required.issubset(set(benchmarks.get("required_real_sessions", []))):
        raise SourceDrift("network benchmark lacks critical actual Bloodborne scenarios")
    stages = policy.get("priority_order", [])
    if (not isinstance(stages, list)
            or [s.get("priority") for s in stages] != [0, 1, 2]):
        raise SourceDrift("P0 core stability must precede optional gameplay changes")
    core = set(stages[0].get("features", []))
    for requirement in ("native_game_boot", "reliable_login_and_discovery",
                        "join_and_host_coop", "opt_in_invasions", "safe_save_backups", "doors_and_npc_signs",
                        "crash_free_2_hour_sessions", "measured_network_load"):
        if requirement not in core:
            raise SourceDrift("missing core release gate: " + requirement)
    invasion = policy.get("invasion_policy", {})
    if (invasion.get("enabled_by_default") is not False
            or invasion.get("require_explicit_match_opt_in") is not True
            or invasion.get("session_permissions_tested") is not False
            or invasion.get("version_and_protocol_compatibility_tested") is not False
            or invasion.get("adversarial_join_tested") is not False):
        raise SourceDrift("unverified PvP invasion mode must be off and require explicit consent")
    if policy.get("no_unreviewed_external_source_code") is not True or (
            policy.get("requires_license_and_original_author_credit") is not True
            or policy.get("release_ready") is not False):
        raise SourceDrift("fork inspirations are not licensed code or a finished release")
    for source in policy.get("design_references", []):
        if source.get("status") not in ("design_ideas_only", "gameplay_concepts_only",
                                        "test_verified_code_only"):
            raise SourceDrift("design inspiration cannot be silently labelled copied code")


def check_policy(meta: dict) -> None:
    if meta.get("schema") != 1 or meta.get("canonical_branch") != CANONICAL:
        raise SourceDrift("not the single Seamless Hunt development branch")
    baseline = meta.get("source_of_truth", {})
    if (baseline.get("repository") != "lKaniel/bloodborne-server"
            or baseline.get("commit") != PIN
            or baseline.get("upstream_tag") != "v1.1.9"):
        raise SourceDrift("pinned Yharnam Together source does not match approved baseline")
    if meta.get("release_ready") is not False or meta.get("fornex_deployment_authorized") is not False:
        raise SourceDrift("source-only project cannot be marked player-ready or production approved")
    components = meta.get("components", {})
    if components.get("game", {}).get("build") != "bbport/build.sh":
        raise SourceDrift("game must compile from Yharnam Together native bbport")
    if components.get("launcher", {}).get("upstream") != "bbport/launcher/bbport_launcher_win.py":
        raise SourceDrift("cannot switch to old master/Visy launcher")
    if components.get("launcher", {}).get("coop") != "bbport/launcher/bbport_coop.py":
        raise SourceDrift("Yharnam Together co-op launcher is mandatory")
    if components.get("server", {}).get("linux", {}).get("os") != "Ubuntu 24.04 x86_64":
        raise SourceDrift("actual Fornex staging host is Ubuntu 24.04, not Debian")
    for osname in ("linux", "windows"):
        if components.get("server", {}).get(osname, {}).get("qt") != "6.8.3":
            raise SourceDrift("real host and Windows test co-op server use Qt 6.8.3")
    for key in ("npc_summon_signs", "guest_interact_doors",
                "cls_ps4_shadps4_bbport_crossplay", "public_room_matchmaking",
                "password_isolation"):
        if key not in meta.get("feature_status", {}).get("not_yet_game_verified", []):
            raise SourceDrift(f"cannot silently certify untested gameplay: {key}")
    rights = meta.get("attribution_and_licenses", {})
    if (rights.get("primary_license_as_documented_upstream") != "GPL-2.0-or-later"
            or rights.get("legacy_repo_root_license") != "GPL-3.0"
            or rights.get("qt_httpserver_6_8_3_open_source_license") != "GPL-3.0 (NOT LGPL-3.0)"
            or rights.get("release_license_audit_completed") is not False
            or rights.get("redistribution_approved") is not False):
        raise SourceDrift("original GPL licenses or the Qt HTTP Server GPLv3 release block changed")
    if set(rights.get("english_docs", [])) != {
            "README.md", "CREDITS.md", "THIRD_PARTY_NOTICES.md", "CONTRIBUTING.md"}:
        raise SourceDrift("English authorship, copyright and license documentation missing")
    if "CREDITS.txt" not in rights.get("game_candidate_notices", []):
        raise SourceDrift("Windows game must show authorship and provenance")
    if "server/licenses/Qt-6.8.3-LICENSE-SCOPE.txt" not in rights.get("server_candidate_notices", []):
        raise SourceDrift("Qt HTTP Server GPLv3 notice missing from Windows host")
    # Do not manufacture a unified player base by putting different
    # networking protocols behind the same address or UI label.
    provider_file = POLICY.with_name("interop_policy.json")
    try:
        interop = json.loads(provider_file.read_text("utf-8"))
    except (ValueError, OSError) as exc:
        raise SourceDrift("Missing audited co-op provider policy") from exc
    check_interop_policy(interop)
    paths = meta.get("mainline_workflows", {})
    if set(paths) != {"windows_game", "windows_server", "linux_server",
                      "event_patch", "package_gate"}:
        raise SourceDrift("client+launcher, Qt servers, package and event gates must all be covered")
    for item in paths.values():
        if not re.fullmatch(r"\.github/workflows/[a-z0-9-]+\.yml", item):
            raise SourceDrift("unsafe or invalid mainline workflow path")


def check_workflow_wiring(meta: dict, workflows: dict[str, str], orchestrator: str) -> None:
    """Verify native reusable jobs are *called* by the canonical, protected entry point.

    A reusable workflow has 'on: workflow_call' and intentionally has no branch
    filter of its own. Requiring CANONICAL in each helper silently blocks all
    builds before Windows or Ubuntu compilation ever starts.
    """
    if (f"branches: [{CANONICAL}]" not in orchestrator
            or "needs: source-contract" not in orchestrator
            or "name: Seamless Hunt native Yharnam Together unified candidate" not in orchestrator):
        raise SourceDrift("canonical mainline entry point or source-contract gate missing")
    for key in ("windows_game", "windows_server", "linux_server"):
        relative = meta["mainline_workflows"][key]
        source = workflows[key]
        if (f"uses: ./{relative}" not in orchestrator
                or "workflow_call:" not in source):
            raise SourceDrift(f"native {key} reusable job disconnected from canonical mainline")
        if PIN not in source:
            raise SourceDrift(f"native {key} no longer pins Yharnam Together")
    # These historical dedicated CI workflows do not have to declare our branch:
    # their actual tests and packaging are explicitly executed by the new caller.
    if ("test_patch_windows_package.py" not in orchestrator
            or "test_windows_candidate.py" not in orchestrator
            or "test_patch_windows_package.py" not in workflows["event_patch"]
            or "test_assemble_windows_test_kit.py" not in orchestrator
            or "assemble_windows_test_kit.py" not in orchestrator
            or "test_assemble_windows_test_kit.py" not in workflows["package_gate"]):
        raise SourceDrift("event/kit safety checks disconnected from canonical candidate")
    if "needs: [windows-game, windows-coop-host, fornex-ubuntu-staging]" not in orchestrator:
        raise SourceDrift("candidate can assemble before native Windows and Ubuntu kits pass")


def check_workspace(root: Path, meta: dict) -> None:
    check_policy(meta)
    transport_file = POLICY.with_name("transport_and_feature_priorities.json")
    check_transport_feature_policy(json.loads(transport_file.read_text("utf-8")))
    composer = (root / meta["overlay_builder"]).read_text("utf-8")
    if (f'PIN = "{PIN}"' not in composer
            or 'LAUNCHER = "bbport/launcher/bbport_launcher_win.py"' not in composer
            or 'COOP = "bbport/launcher/bbport_coop.py"' not in composer
            or "output[HTTP_BACKEND_CPP]" not in composer
            or 'dest[LAUNCHER]=v8patch.patch_launcher(source[LAUNCHER])' not in composer
            or '"public_release_ready":False' not in composer):
        raise SourceDrift("composed Yharnam Together client, launcher or server not pinned")
    # A game pointing at Fornex staging MUST be able to select its actual
    # isolated ports without swapping away from upstream BLauncher or touching
    # the production CLS 31314/31315/20443 network.
    profile_patch = (root / "tools/poc/yharnam/remote-profile-v46/patch_remote_ports.py").read_text("utf-8")
    if ('"SHYT-V46-EXPLICIT-REMOTE-PORTS"' not in profile_patch
            or '"SHADNET_PORT, WEBAPI_PORT, MATCHING_PORT, BACKEND_PORT = 31313, 31315, 31314, 20443"' not in profile_patch
            or "remote-profile-v46/patch_remote_ports.py" not in composer
            or "V46 explicit guest-only remote staging UDP/WebAPI/backend ports" not in composer):
        raise SourceDrift("missing opt-in real Fornex IPv4 guest endpoints from original Yharnam launcher")
    game_package = (root / "tools/poc/yharnam/package-v40/patch_windows_package.py").read_text("utf-8")
    if ('SeamlessHunt-network-profile.example.json' not in game_package
            or "Missing example for isolated remote co-op ports" not in game_package):
        raise SourceDrift("portable game kit cannot show safe alternate server profile")
    release = (root / "tools/poc/yharnam/release-v8/patch_update_channel.py").read_text("utf-8")
    if (f'PIN="{PIN}"' not in release
            or "SH_RELEASE_PREFIX = 'shyt-v'" not in release):
        raise SourceDrift("launcher updater could target an unrelated project")
    workflow_sources = {
        key: (root / relative).read_text("utf-8")
        for key, relative in meta["mainline_workflows"].items()
    }
    orchestrator = (root / ".github/workflows/shyt-mainline-candidate.yml").read_text("utf-8")
    check_workflow_wiring(meta, workflow_sources, orchestrator)
    for key, data in workflow_sources.items():
        if "runs-on: windows-2022" not in data and key in {"windows_game", "windows_server"}:
            raise SourceDrift("native Windows builds must actually run on Windows")
        if key == "linux_server" and ("runs-on: ubuntu-24.04" not in data or "'6.8.3'" not in data):
            raise SourceDrift("real Ubuntu 24.04 / Qt 6.8.3 server build missing")
    rights = meta["attribution_and_licenses"]
    for doc in rights["english_docs"]:
        contents = (root / doc).read_text("utf-8")
        if "Yharnam Together" not in contents or len(contents) < 200:
            raise SourceDrift("missing primary upstream authorship in " + doc)
    copyright_notice = (root / "tools/poc/yharnam/attribution-v42/CREDITS.txt").read_text("utf-8")
    for name in ("Yharnam Together", "deadinside28", "Supermedo",
                 "Wozzardman", "shadPS4", "0xCydral", "GPL-2.0-or-later",
                 "Qt 6.8 HTTP Server is GPL-3.0"):
        if name not in copyright_notice:
            raise SourceDrift("downstream Windows user-facing CREDITS missing " + name)
    game_packaging = (root / "tools/poc/yharnam/package-v40/patch_windows_package.py").read_text("utf-8")
    if ('cp "$credits" "$dest/CREDITS.txt"' not in game_packaging
            or "FireBurn-FSR-Vulkan-LICENSE.txt" not in game_packaging):
        raise SourceDrift("portable launcher would omit credits or upstream runtime licenses")
    game = (root / meta["mainline_workflows"]["windows_game"]).read_text("utf-8")
    if ("pinned-upstream/bbport" not in game or "bash build.sh" not in game
            or "bash packaging/windows/package.sh" not in game
            or "tools/poc/yharnam/package-v40/patch_windows_package.py" not in game):
        raise SourceDrift("Windows client build/launcher missing native Yharnam/game event packager")
    host = (root / meta["mainline_workflows"]["windows_server"]).read_text("utf-8")
    if ("shadnet" not in host or "windeployqt.exe" not in host): 

        raise SourceDrift("Windows co-op host kit must include actual Qt server runtime")
    if ("Qt-6.8.3-LICENSE-SCOPE.txt" not in host
            or 'Copy-Item LICENSE "$out/server/licenses/GPL-3.0.txt"' not in host):
        raise SourceDrift("Windows Qt HTTP Server GPLv3-only notice absent from candidate")



def main() -> int:
    try:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        check_workspace(REPO_ROOT, policy)
    except (OSError, ValueError, KeyError) as error:
        print("SH_MAINLINE_SOURCE_DRIFT_FAIL:", error, file=sys.stderr)
        return 1
    print("SH_MAINLINE_YHARNAM_TOGETHER_SOURCE_PASS")
    print("Baseline: lKaniel/bloodborne-server@" + PIN)
    print("Native game, BLauncher, co-op backend, Ubuntu 24.04 and Windows Qt 6.8.3: correctly routed")
    print("WARNING: source provenance only; no crossplay or real gameplay claim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
