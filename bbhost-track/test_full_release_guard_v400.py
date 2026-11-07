#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fictional proof tests; shipping must refuse untested real-game runtime."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile

from full_release_guard_v400 import (
    ShipRefused,REQUIRED,read_manifest,gaps,can_ship
)
SOURCE=Path(__file__).resolve().parent/"full_release_contract_v400.json"

def refuses(fn):
    try:
        fn()
    except ShipRefused:
        return
    raise AssertionError("unverified or malformed release was accepted")

def test()->None:
    contract=read_manifest(SOURCE)
    assert len(REQUIRED)==19
    assert len(gaps(contract))==19
    refuses(lambda:can_ship(contract))
    with tempfile.TemporaryDirectory(prefix="shyt-v400-no-release-") as t:
        p=Path(t)/"fictional-candidate.json"
        def read(obj):
            p.write_text(json.dumps(obj),encoding="utf-8")
            return read_manifest(p)
        m=copy.deepcopy(contract)
        m["gates"].pop("p2p_direct_authenticated")
        refuses(lambda:read(m))
        m=copy.deepcopy(contract)
        m["kind"]="SINGLE_TEST_DLL_DOWNLOAD"
        refuses(lambda:read(m))
        m=copy.deepcopy(contract)
        m["candidate_package_sha256"]="x"*64
        refuses(lambda:read(m))
        m=copy.deepcopy(contract)
        m["gates"]["five_player_coop"]["status"]="verified"
        refuses(lambda:can_ship(read(m)))
        m=copy.deepcopy(contract)
        m["gates"]["five_player_coop"]["evidence"]=[{
            "type":"github_ci",
            "url":"https://github.com/example/test/actions/runs/1",
            "candidate_package_sha256":"1"*64
        }]
        refuses(lambda:read(m))
        m=copy.deepcopy(contract)
        m["candidate_source_sha"]="2"*40
        m["candidate_package_sha256"]="1"*64
        for gate in m["gates"].values():
            gate["status"]="verified"
            gate["evidence"]=[{
                "type":"github_ci",
                "url":"https://github.com/example/test/actions/runs/1",
                "candidate_package_sha256":"1"*64
            }]
        # Fake green CI alone is NOT a real game, online, installer, or
        # full-package sign-off; proof TYPES are mandatory in release mode.
        refuses(lambda:can_ship(read(m)))
        m["gates"]["real_two_pc_acceptance"]["evidence"][0]["candidate_package_sha256"]="3"*64
        refuses(lambda:can_ship(read(m)))
        m=copy.deepcopy(contract)
        m["gates"]["five_player_coop"]["status"]=True
        refuses(lambda:read(m))

if __name__=="__main__":
    test()
    print("SHYT_V400_RELEASE_GUARD_BLOCKS_INCOMPLETE_OR_FICTIONAL_SHIP_PASS")
