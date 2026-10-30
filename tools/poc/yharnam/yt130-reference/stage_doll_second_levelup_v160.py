#!/usr/bin/env python3
"""V160 source-exact upstream YT #468 Doll second level-up follow-up, on V151.

After original YT1.3 source is staged through V151/#457, apply ONLY the
four original native C++/test-file changes in upstream #468. This fixes
guest second "Level Up" when its own talk requests blessing 72100100 but
the flag never becomes true in that guest's game. Mark own talk request
atomically, consume on next tick (never within the talk callback), clear 6700.
No game assets, saves, online protocol or server changed.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
REVIEWED="b18c5f371a19ca9a605e8fc40f8a57876ed12aac"
FILES={
    "emulator/src/core/bloodborne_party.cpp":
        ("5186b4ed9fa9387752f4dc21362950d70d062505",
         "d2ae38caaae28f3a3b8d51023c5dc3e4f3a5a9dc"),
    "emulator/src/core/bloodborne_party.h":
        ("dc42d0509461fda6f557fa88f98a29fa28d877af",
         "d0320e3a7329bef000146fffc0be35c135523c84"),
    "emulator/src/core/bloodborne_travel.cpp":
        ("cf8112da1c9f897cdeb254d8f592edf12e74e57f",
         "f35bfb1df26fb7111c499f3e2a36f2f27b0070ad"),
    "emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp":
        ("5adbed2977d43efbdde41051c8e41060464c2301",
         "c297b6ab7b78cc9604fcca9f2462c5a56c812752"),
}
CPP="emulator/src/core/bloodborne_party.cpp"
HEADER="emulator/src/core/bloodborne_party.h"
TRAVEL="emulator/src/core/bloodborne_travel.cpp"
TEST="emulator/tests/bloodborne/test_bloodborne_flag_rules.cpp"
CPP_START="bool ClearsDollLevelUpFlagOnHerBlessing(bool party_configured, bool others_talk,\n"
CPP_AFTER="\nstd::vector<s32> LightRequestsToClear("
HEADER_START="// The rig 2026-10-30: in a guest's game her talk's request for 72100100"
HEADER_AFTER="// The other player's \"set this event flag\""
TRAVEL_ATOMIC_START="// This player's talk asked for the Doll's blessing (see ClearsDollLevelUpFlagOnHerBlessing).\n"
TRAVEL_ATOMIC_END="\n} // namespace\n"
TRAVEL_HOOK_START="    // See ClearsDollLevelUpFlagOnHerBlessing: cleared by the next tick\n"
TRAVEL_HOOK_END="    // An NPC's gift (common event 9100 ends for a phantom)"
TRAVEL_TICK="void ClearDollLevelUpFlagAfterHerMenu() {\n"
TRAVEL_TICK_END="\n// See ImpurityBonusChange: every second, the Impurity rune's HP bonus put on"
TEST_START="// The rig 2026-10-30 (doll-level-up-cancelled): in a guest's game her talk asks"
TEST_AFTER="// Kaniel 2026-10-30: the host's level up played the kneel on guests."
EXPECTED_HELPER=(
    "bool ClearsDollLevelUpFlagOnHerBlessing(bool party_configured, bool others_talk,\n"
    "                                        s32 requested_flag) {\n"
    "    return party_configured && !others_talk && requested_flag == DollBlessingFlag;\n"
    "}\n"
)

def git(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],
                                   encoding="utf-8",stderr=subprocess.DEVNULL).strip()

def norm(raw:bytes)->bytes:
    return raw.replace(b"\r\n",b"\n")

def blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()

def region(s:str,start:str,end:str,label:str)->str:
    if s.count(start)!=1:
        raise ValueError("V160 exact upstream start drift: "+label)
    at=s.index(start)
    stop=s.find(end,at+len(start))
    if stop<0:
        raise ValueError("V160 upstream end drift: "+label)
    return s[at:stop]

def one(s:str,old:str,new:str,label:str)->str:
    if s.count(old)!=1 or (new!=old and new in s):
        raise ValueError("V160 original staged #457 source drift: "+label)
    return s.replace(old,new,1)

def patch(name:str,base:str,head:str)->str:
    if "ClearsDollLevelUpFlagAfterHerMenu" not in base or (
        "ClearsDollLevelUpFlagOnHerBlessing" in base):
        raise ValueError("V160 requires precisely V151 prior staged Doll helper")
    if name==CPP:
        helper=region(head,CPP_START,CPP_AFTER,"new exact helper")
        if helper.strip()!=EXPECTED_HELPER.strip() or helper.count("return ")!=1:
            raise ValueError("V160 reviewed own-talk predicate drift")
        return one(base,CPP_AFTER,"\n"+helper+CPP_AFTER,"native own-talk helper")
    if name==HEADER:
        fragment=region(head,HEADER_START,HEADER_AFTER,"native declaration")
        if ("bool ClearsDollLevelUpFlagOnHerBlessing" not in fragment
                or len(fragment)>800):
            raise ValueError("V160 reviewed native helper declaration drift")
        return one(base,HEADER_AFTER,fragment+HEADER_AFTER,"native own-talk header")
    if name==TRAVEL:
        atomic=region(head,TRAVEL_ATOMIC_START,TRAVEL_ATOMIC_END,"atomic flag")
        if "std::atomic<bool> doll_blessing_asked{};" not in atomic or len(atomic)>300:
            raise ValueError("V160 reviewed native own-talk atomic drift")
        base=one(base,"thread_local u64 esd_talker = 0;\n",
                 "thread_local u64 esd_talker = 0;\n"+atomic,"atomic own-talk")
        hook=region(head,TRAVEL_HOOK_START,TRAVEL_HOOK_END,"guest own talk hook")
        if ("doll_blessing_asked.store(true);" not in hook or
                "esd_talker != GetLocalPlayer()" not in hook or len(hook)>900):
            raise ValueError("V160 reviewed talk hook drift")
        base=one(base,TRAVEL_HOOK_END,hook+TRAVEL_HOOK_END,"on-talk own blessing")
        old=region(base,TRAVEL_TICK,TRAVEL_TICK_END,"original V151 next tick")
        new=region(head,TRAVEL_TICK,TRAVEL_TICK_END,"upstream #468 next tick")
        if (len(new)>1100 or "doll_blessing_asked.exchange(false)" not in new or
                "asked || EventFlagOn(DollBlessingFlag)" not in new or
                "PartyGhostSetEventFlagOffset" not in new):
            raise ValueError("V160 original game next-tick semantics drift")
        return one(base,old,new,"atomic own talk trigger consumed next tick")
    if name==TEST:
        code=region(head,TEST_START,TEST_AFTER,"upstream actual gtest")
        if (len(code)>1700 or
            "TEST(BloodborneFlagRules, TheDollsLevelUpFlagGoesOffAsHerTalkAsksForHerBlessing)" not in code or
            code.count("EXPECT_FALSE(")!=4 or code.count("EXPECT_TRUE(")!=1):
            raise ValueError("V160 expected original game regression changed")
        return one(base,TEST_AFTER,code+TEST_AFTER,"real Bloodborne flag regression")
    raise ValueError("V160 unrelated game source refused")

def stage(original:Path,reviewed:Path)->None:
    original=original.resolve(strict=True)
    reviewed=reviewed.resolve(strict=True)
    if (git(original,"rev-parse","HEAD")!=PIN or
            git(reviewed,"rev-parse","HEAD")!=REVIEWED):
        raise ValueError("V160 original pinned or upstream #468 review source changed")
    out=[]
    for path,(original_blob,review_blob) in FILES.items():
        target=original/path
        source=reviewed/path
        if (not target.is_file() or target.is_symlink() or
            not source.is_file() or source.is_symlink() or
            git(original,"rev-parse","HEAD:"+path)!=original_blob or
            git(reviewed,"rev-parse","HEAD:"+path)!=review_blob):
            raise ValueError("V160 original/actual reviewed Git file blob mismatch "+path)
        base=norm(target.read_bytes())
        head=norm(source.read_bytes())
        if blob(head)!=review_blob:
            raise ValueError("V160 reviewed actual Git source contents changed "+path)
        patched=patch(path,base.decode("utf-8"),head.decode("utf-8"))
        if patched.encode("utf-8")==base:
            raise ValueError("V160 patch would be empty")
        out.append((target,patched.encode("utf-8")))
    # Fail-closed review: all four staged C++ candidates before any writes.
    for file,data in out:
        file.write_bytes(data)
    subprocess.run(["git","-C",str(original),"diff","--check"],check=True)
    print("SHYT_V160_ORIGINAL_YT130_DOLL_REPEAT_LEVELUP_GUEST_BLESSING_STAGED")

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--original",required=True,type=Path)
    a.add_argument("--reviewed",required=True,type=Path)
    x=a.parse_args()
    stage(x.original,x.reviewed)
