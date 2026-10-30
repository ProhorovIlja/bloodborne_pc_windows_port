#!/usr/bin/env python3
"""V151: source-exact native YT1.3 Doll co-op fixes from reviewed upstream #457.

Why: a guest's 6700 Doll level-up menu flag stays set after the first menu,
and the host's blessing flags 72100100-72100102 used to become guest story
steps and drive a spurious kneel. Keep these flags per-player, and clear 6700
only when its own closed-menu blessing was actually set.

Changes exactly 7 original native game / regression files, NEVER original
asset files, gameplay protocol, server DB, persistent saves or production.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess

BASE_PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
REVIEWED_PIN="3ce88c205648616b52b729fc2764b6fe27f7af83"
FILES={
    "emulator/src/core/bloodborne_flags.h":
        ("64366ea81f595e1892e468e60090dc42e80b500c","f0ebdbaf4e250c6c2ae9e897f05c640fb15ee115"),
    "emulator/src/core/bloodborne_party.cpp":
        ("5186b4ed9fa9387752f4dc21362950d70d062505","bdedb1576e9e8f4b702b7fc4a75b037c91ae84d0"),
    "emulator/src/core/bloodborne_party.h":
        ("dc42d0509461fda6f557fa88f98a29fa28d877af","913b9b606963afb54cfef7463dbf54f4d679a99c"),
    "emulator/src/core/bloodborne_travel.cpp":
        ("cf8112da1c9f897cdeb254d8f592edf12e74e57f","11bef12a35ddf98f52ff8acbe2f428a0cb06383b"),
    "emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp":
        ("5adbed2977d43efbdde41051c8e41060464c2301","b3bb9679c78c518e6f081fec30bef17e98b9e728"),
    "emulator/tests/bloodborne/test_bloodborne_team.cpp":
        ("471e5f3656ee2e31c45b38cb6961b30629d41e7d","b42fa25c5339653d8d6f062fd4f83c2ffe04929d"),
    "emulator/tests/bloodborne/flag_rules_expected.txt":
        ("8fcc3a1a20c963d6c05577735a060b432a1b12f1","35e8fdf0049ea51b2091181ec8e8d62bc369148d"),
}
GAME="emulator/src/core/bloodborne_party.cpp"
HELPER_START="bool ClearsDollLevelUpFlagAfterHerMenu(bool party_configured, bool level_up_on, bool blessing_on) {\n"
HELPER_END="\nstd::vector<s32> LightRequestsToClear("
OLD_CLEAR=("bool ClearsDollLevelUpFlag(bool party_configured, bool flag_on) {\n"
           "    return party_configured && flag_on;\n"
           "}\n\n")
RULE_OLD='    Range(6700, 6700, FlagOwner::PerPlayer, 0,\n'
RULE_NEXT='    Range(6744, 6747, FlagOwner::PerPlayer, FlagCarriesHome,\n'
RULE_INSERT='    Range(72100100, 72100102, FlagOwner::PerPlayer, 0,\n'
RULE_AFTER='    Range(72100300, 72100309, FlagOwner::Session, 0,\n'
PARTY_DECL=("constexpr s32 DollLevelUpFlag = 6700;\n"
            "bool ClearsDollLevelUpFlag(bool party_configured, bool flag_on);\n")
TRAVEL_INSERT=("// See ClearsDollLevelUpFlagAfterHerMenu: every frame in a party (her blessing can be over within a\n")
TRAVEL_AFTER="// See ImpurityBonusChange: every second, the Impurity rune's HP bonus put on (through the\n"
TRAVEL_CALL="    KeepHeadstoneFlagsOwn();\n"
TEST_FLAG_START="// Kaniel 2026-10-30: guests could not level up again in the same Dream visit."
TEST_FLAG_AFTER="// m21_00 12105020-12105024 (01.09): on while any of the headstone's lamps is lit."
TEST_TEAM_START="// Kaniel 2026-10-30: when the host levelled up in the Dream, guests knelt too."
TEST_TEAM_AFTER="// Kaniel's playtest 2026-10-22: a guest alone on a map saw NPCs the team's world has gone past"
EXPECTED_OLD="70000008 8\n72100300 0\n"
EXPECTED_NEW="70000008 8\n72100100 20\n72100103 8\n72100300 0\n"

def git(root: Path,*args: str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],
                                   encoding="utf-8",stderr=subprocess.DEVNULL).strip()

def blob_sha(raw: bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()

def normalized(raw: bytes)->bytes:
    return raw.replace(b"\r\n",b"\n")

def exactly(s: str,old: str,new: str,label: str)->str:
    if s.count(old)!=1 or (old!=new and new in s):
        raise ValueError("V151 original source or duplicate drift "+label)
    return s.replace(old,new,1)

def region(src:str,start:str,end:str,label:str)->str:
    if src.count(start)!=1:
        raise ValueError("V151 reviewed source region start drift "+label)
    at=src.index(start)
    stop=src.find(end,at+len(start))
    if stop<0:
        raise ValueError("V151 reviewed source region end drift "+label)
    return src[at:stop]

def apply(name:str,original:str,reviewed:str)->str:
    if name.endswith("/bloodborne_flags.h"):
        b=region(original,RULE_OLD,RULE_NEXT,"original Doll rule")
        n=region(reviewed,RULE_OLD,RULE_NEXT,"upstream Doll rule")
        if len(n)>850 or len(b)>850 or "ClearsDollLevelUpFlagAfterHerMenu" not in n:
            raise ValueError("V151 unexpected upstream Doll rule size/semantics")
        original=exactly(original,b,n,"Doll menu 6700 rule")
        row=region(reviewed,RULE_INSERT,RULE_AFTER,"upstream local 72100100 rule")
        if len(row)>750 or "the Doll's blessing" not in row:
            raise ValueError("V151 unexpected per-player flags rule")
        original=exactly(original,RULE_AFTER,row+RULE_AFTER,"72100100-72100102 own")
        return original
    if name.endswith("/bloodborne_party.cpp"):
        helper=region(reviewed,HELPER_START,HELPER_END,"upstream Doll helper")
        if helper.strip()!=(
            "bool ClearsDollLevelUpFlagAfterHerMenu(bool party_configured, bool level_up_on, bool blessing_on) {\n"
            "    return party_configured && level_up_on && blessing_on;\n"
            "}"
        ):
            raise ValueError("V151 reviewed Doll menu-close semantics changed")
        return exactly(original,OLD_CLEAR,OLD_CLEAR+helper,"menu closed helper")
    if name.endswith("/bloodborne_party.h"):
        added=region(reviewed,
            "// Kaniel 2026-10-30: a guest's 6700 stayed on after her level-up menu closed",
            "// The other player's \"set this event flag\"",
            "upstream Doll helper declarations")
        if "constexpr s32 DollBlessingFlag = 72100100;" not in added or len(added)>1000:
            raise ValueError("V151 wrong Doll helper declaration")
        return exactly(original,PARTY_DECL,PARTY_DECL+added,"native Doll helper declaration")
    if name.endswith("/bloodborne_travel.cpp"):
        body=region(reviewed,TRAVEL_INSERT,TRAVEL_AFTER,"upstream native Doll tick")
        if "void ClearDollLevelUpFlagAfterHerMenu()" not in body or len(body)>1600:
            raise ValueError("V151 wrong original native Doll tick")
        original=exactly(original,TRAVEL_AFTER,body+TRAVEL_AFTER,"native tick implementation")
        original=exactly(original,TRAVEL_CALL,TRAVEL_CALL+
                         "    ClearDollLevelUpFlagAfterHerMenu();\n",
                         "one per-frame own Doll menu clear")
        return original
    if name.endswith("/test_bloodborne_flag_rules.cpp"):
        body=region(reviewed,TEST_FLAG_START,TEST_FLAG_AFTER,"upstream Doll rule regression")
        if (len(body)>2700 or
            "TEST(BloodborneFlagRules, TheDollsLevelUpFlagGoesOffOnceHerMenuClosed)" not in body or
            "TEST(BloodborneFlagRules, TheDollsBlessingFlagsAreEachGamesOwn)" not in body):
            raise ValueError("V151 wrong upstream Doll flag tests")
        return exactly(original,TEST_FLAG_AFTER,body+TEST_FLAG_AFTER,"native Doll flag regressions")
    if name.endswith("/test_bloodborne_team.cpp"):
        body=region(reviewed,TEST_TEAM_START,TEST_TEAM_AFTER,"upstream Doll story regression")
        if len(body)>1400 or "TEST(TeamWorld, AGuestKeepsItsOwnDollBlessingFlags)" not in body:
            raise ValueError("V151 wrong upstream Doll story test")
        return exactly(original,TEST_TEAM_AFTER,body+TEST_TEAM_AFTER,"Doll team story regression")
    if name.endswith("/flag_rules_expected.txt"):
        if EXPECTED_NEW not in reviewed:
            raise ValueError("V151 upstream rule snapshot changed")
        return exactly(original,EXPECTED_OLD,EXPECTED_NEW,"native flag snapshot")
    raise ValueError("V151 refused unrelated native source file")

def stage(base:Path,upstream:Path)->None:
    base=base.resolve()
    upstream=upstream.resolve()
    if git(base,"rev-parse","HEAD")!=BASE_PIN or git(upstream,"rev-parse","HEAD")!=REVIEWED_PIN:
        raise ValueError("V151 source-verified original or upstream revision changed")
    output=[]
    # Verify every input in full BEFORE writing any file.
    for name,(old_sha,review_sha) in FILES.items():
        src=base/name
        ref=upstream/name
        if (not src.is_file() or src.is_symlink() or
            not ref.is_file() or ref.is_symlink() or
            git(base,"rev-parse","HEAD:"+name)!=old_sha or
            git(upstream,"rev-parse","HEAD:"+name)!=review_sha):
            raise ValueError("V151 exact original/reviewed source path/hash missing "+name)
        old,review=normalized(src.read_bytes()),normalized(ref.read_bytes())
        if blob_sha(old)!=old_sha or blob_sha(review)!=review_sha:
            raise ValueError("V151 original/reviewed Git blob changed "+name)
        new=apply(name,old.decode("utf-8"),review.decode("utf-8"))
        if old==new.encode("utf-8"):
            raise ValueError("V151 empty review change "+name)
        output.append((src,new.encode("utf-8")))
    for target,data in output:
        target.write_bytes(data)
    print("SHYT_V151_EXACT_ORIGINAL_YT130_DOLL_FLAG_FIX_STAGED_NOT_GAMEPLAY")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--original",type=Path,required=True)
    parser.add_argument("--reviewed",type=Path,required=True)
    args=parser.parse_args()
    stage(args.original,args.reviewed)
