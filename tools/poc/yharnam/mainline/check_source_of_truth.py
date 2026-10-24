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
    paths = meta.get("mainline_workflows", {})
    if set(paths) != {"windows_game", "windows_server", "linux_server",
                      "event_patch", "package_gate"}:
        raise SourceDrift("client+launcher, Qt servers, package and event gates must all be covered")
    for item in paths.values():
        if not re.fullmatch(r"\.github/workflows/[a-z0-9-]+\.yml", item):
            raise SourceDrift("unsafe or invalid mainline workflow path")


def check_workspace(root: Path, meta: dict) -> None:
    check_policy(meta)
    composer = (root / meta["overlay_builder"]).read_text("utf-8")
    if (f'PIN = "{PIN}"' not in composer
            or 'LAUNCHER = "bbport/launcher/bbport_launcher_win.py"' not in composer
            or 'COOP = "bbport/launcher/bbport_coop.py"' not in composer
            or "output[HTTP_BACKEND_CPP]" not in composer
            or 'dest[LAUNCHER]=v8patch.patch_launcher(source[LAUNCHER])' not in composer
            or '"public_release_ready":False' not in composer):
        raise SourceDrift("composed Yharnam Together client, launcher or server not pinned")
    release = (root / "tools/poc/yharnam/release-v8/patch_update_channel.py").read_text("utf-8")
    if (f'PIN="{PIN}"' not in release
            or "SH_RELEASE_PREFIX = 'shyt-v'" not in release):
        raise SourceDrift("launcher updater could target an unrelated project")
    for key, relative in meta["mainline_workflows"].items():
        data = (root / relative).read_text("utf-8")
        if CANONICAL not in data:
            raise SourceDrift(f"workflow for {key} does not build canonical mainline")
        if key in {"windows_game", "windows_server", "linux_server"} and PIN not in data:
            raise SourceDrift(f"workflow for {key} compiles unpinned upstream")
        if "runs-on: windows-2022" not in data and key in {"windows_game", "windows_server"}:
            raise SourceDrift("native Windows builds must actually run on Windows")
        if key == "linux_server" and ("runs-on: ubuntu-24.04" not in data or "'6.8.3'" not in data):
            raise SourceDrift("real Ubuntu 24.04 / Qt 6.8.3 server build missing")
    game = (root / meta["mainline_workflows"]["windows_game"]).read_text("utf-8")
    if ("pinned-upstream/bbport" not in game or "bash build.sh" not in game
            or "bash packaging/windows/package.sh" not in game
            or "tools/poc/yharnam/package-v40/patch_windows_package.py" not in game):
        raise SourceDrift("Windows client build/launcher missing native Yharnam/game event packager")
    host = (root / meta["mainline_workflows"]["windows_server"]).read_text("utf-8")
    if ("shadnet" not in host or "windeployqt6.exe" not in host):
        raise SourceDrift("Windows co-op host kit must include actual Qt server runtime")


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
