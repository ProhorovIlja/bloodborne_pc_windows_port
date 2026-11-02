#!/usr/bin/env python3
"""Source-locked candidate check of upstream YT 1.3.2 PR #484, NOT a release.

Checks the ORIGINAL upstream 5-seat server, emulator, portraits and game HUD
move together. Does not copy gameplay into our project or claim live play.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess

PR484_SHA = "f19696f32833161aa2300b36321d8c5c4d663c6b"

def check(root: Path) -> None:
    if subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip() != PR484_SHA:
        raise ValueError("upstream five-player candidate SHA changed")

    def source(name: str) -> str:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("required original five-player source missing")
        return path.read_text(encoding="utf-8")

    def require(pattern: str, name: str) -> None:
        if not re.search(pattern, source(name), re.MULTILINE | re.DOTALL):
            raise ValueError("candidate five-player subsystem mismatch: " + name)

    require(r"\bTeamSize\s*=\s*5\s*;", "server/coop/team_lobby.h")
    require(r"\bGuestSigns\s*\{\s*7\s*,\s*6\s*,\s*5\s*,\s*4\s*\}",
            "server/coop/team_lobby.cpp")
    require(r"\bInvasionMaxPlayers\s*=\s*5\s*;", "server/coop/invasions.h")
    require(r"\bPartyListSize\s*=\s*4\s*;", "emulator/src/core/bloodborne_party.h")
    require(r"\bPortraitSlotCount\s*=\s*4\s*;", "emulator/src/core/bloodborne_portrait.h")
    require(r"\bSlotCount\s*=\s*4\s*;", "bbport/gpu/shim/bbport_portraits.h")
    require(r"\bBBCOOP_LOBBY_TEAM\s*=\s*5\s*,", "bbport/gpu/bbcoop.h")
    require(r"CoopParty0.*CoopParty1.*CoopParty2.*CoopParty3",
            "bbport/scripts/hud_patch.py")
    require(r"CoopPartyFace0.*CoopPartyFace1.*CoopPartyFace2.*CoopPartyFace3",
            "bbport/scripts/hud_patch.py")
    require(r"\bTeamHoldsFive\s*\(", "server/tests/test_team_lobby.cpp")
    require(r"\bGuestSigns\b", "server/coop/team_lobby.cpp")

    print("SHYT_YT132_PR484_FIVE_SEAT_CROSS_LAYER_SOURCE_CONTRACT_PASS")
    print("Draft upstream candidate only; no five-game gameplay test or P2P proof.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", required=True, type=Path)
    args = parser.parse_args()
    check(args.checkout)
