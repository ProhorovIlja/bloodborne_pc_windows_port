#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""No half-ready download: a fail-closed release readiness policy.

Audit just checks the policy's shape and prints what is NOT ready.
Ship refuses until ALL critical runtime/online/installer/staging gates
have real evidence for exactly the same immutable build. A JSON alone
is not a cryptographic attestation. Protected release permissions,
independent manual verification and the owner's approval remain required.
No GitHub release, Fornex deploy or public download is performed here.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

PRODUCT="Bloodborne Seamless Hunt BBHost × Yharnam Together"
KIND="SINGLE_PACKAGE_SHIP_NO_PIECEMEAL_TEST_DOWNLOADS"
POLICY="DO_NOT_PUBLISH_UNTIL_REAL_GAME_AND_STAGING_PROOFS"
REQUIRED=(
    "runtime_game","yt_real_game_hook","server_shlk_authenticated",
    "server_room_lifecycle","five_player_coop","coop_invasions",
    "world_enemy_boss_sync","gameplay_qol","p2p_direct_authenticated",
    "p2p_relay_fallback","matchmaking_invites","launcher_gui_and_settings",
    "performance_stability","server_ops","installer_distribution",
    "docs_support","privacy_security","real_two_pc_acceptance",
    "release_owner_approval",
)
SHA40=re.compile(r"[0-9a-f]{40}\Z")
SHA64=re.compile(r"[0-9a-f]{64}\Z")
# No arbitrary public URL claimed as proof; each proof is package-pinned
# and must still be reviewed by a release authority outside this utility.
PROOFS={"github_ci","real_game_capture","real_two_pc","staging_server",
        "security_review","package_signature","owner_approval","docs_review",
        "performance_measurement","rollback_test"}

class ShipRefused(ValueError):
    pass

def read_manifest(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or not 64<path.stat().st_size<64000:
        raise ShipRefused("missing or unsafe release manifest")
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,ValueError) as e:
        raise ShipRefused("invalid JSON release policy") from e
    if not isinstance(obj,dict) or set(obj)!={
        "schema","product","kind","release_policy","candidate_source_sha",
        "candidate_package_sha256","gates"
    }:
        raise ShipRefused("release policy keys do not match")
    if type(obj["schema"]) is not int or obj["schema"]!=1 or \
       obj["product"]!=PRODUCT or obj["kind"]!=KIND or \
       obj["release_policy"]!=POLICY:
        raise ShipRefused("unknown release product or altered policy")
    gates=obj["gates"]
    if not isinstance(gates,dict) or set(gates)!=set(REQUIRED):
        raise ShipRefused("missing or unexpected hard release gate")
    for name,gate in gates.items():
        if not isinstance(gate,dict) or set(gate)!={"requirement","status","evidence"}:
            raise ShipRefused("invalid release gate fields")
        if not isinstance(gate["requirement"],str) or not 15<len(gate["requirement"])<300:
            raise ShipRefused("missing meaningful user acceptance requirement")
        if gate["status"] not in ("not_verified","verified"):
            raise ShipRefused("invalid gate state")
        if not isinstance(gate["evidence"],list) or len(gate["evidence"])>16:
            raise ShipRefused("invalid evidence list")
        if gate["status"]=="not_verified" and gate["evidence"]:
            raise ShipRefused("unverified gates cannot claim supporting evidence")
        for proof in gate["evidence"]:
            if not isinstance(proof,dict) or set(proof)!={
                "type","url","candidate_package_sha256"
            } or proof["type"] not in PROOFS or \
               not isinstance(proof["url"],str) or \
               not proof["url"].startswith("https://") or \
               not 14<len(proof["url"])<=400 or \
               not isinstance(proof["candidate_package_sha256"],str) or \
               not SHA64.fullmatch(proof["candidate_package_sha256"]):
                raise ShipRefused("invalid scoped external proof")
    for key,expression in (("candidate_source_sha",SHA40),
                           ("candidate_package_sha256",SHA64)):
        value=obj[key]
        if value is not None and (
            not isinstance(value,str) or not expression.fullmatch(value)
        ):
            raise ShipRefused("invalid immutable candidate identity")
    return obj

def gaps(obj:dict)->list[str]:
    return [name for name in REQUIRED
            if obj["gates"][name]["status"]!="verified"]

def can_ship(obj:dict)->None:
    missing=gaps(obj)
    if missing:
        raise ShipRefused("missing real game and staging acceptance gates")
    if not obj["candidate_source_sha"] or not obj["candidate_package_sha256"]:
        raise ShipRefused("no immutable single-product installer candidate")
    for name in REQUIRED:
        evidence=obj["gates"][name]["evidence"]
        if not evidence or any(
            x["candidate_package_sha256"]!=obj["candidate_package_sha256"]
            for x in evidence
        ):
            raise ShipRefused("unproved or mixed-build shipping gate")
    for gate,kind in (
        ("runtime_game","real_game_capture"),
        ("five_player_coop","real_two_pc"),
        ("server_shlk_authenticated","staging_server"),
        ("p2p_direct_authenticated","staging_server"),
        ("p2p_relay_fallback","staging_server"),
        ("installer_distribution","package_signature"),
        ("real_two_pc_acceptance","real_two_pc"),
        ("release_owner_approval","owner_approval"),
    ):
        if not any(p["type"]==kind for p in obj["gates"][gate]["evidence"]):
            raise ShipRefused("mandatory real-usage evidence type absent")

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--mode",choices=("audit","ship"),default="audit")
    args=p.parse_args()
    try:
        obj=read_manifest(args.manifest)
        missing=gaps(obj)
        print("SHYT_V400_COMPLETE_PRODUCT_MANDATORY_GATES=%d"%len(REQUIRED))
        print("SHYT_V400_UNVERIFIED=%d"%len(missing))
        print("SHYT_V400_BLOCKERS="+",".join(missing))
        if args.mode=="ship":
            can_ship(obj)
            print("SHYT_V400_MANIFEST_ELIGIBLE_FOR_INDEPENDENT_RELEASE_REVIEW")
            print("NOT a release, a live gameplay test, a signature check or owner approval.")
        else:
            print("SHYT_V400_POLICY_VALIDATED_NOT_A_SHIPPING_AUTHORIZATION")
        return 0
    except (OSError,ShipRefused) as e:
        print("SHYT_V400_SHIP_REFUSED: "+str(e))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
