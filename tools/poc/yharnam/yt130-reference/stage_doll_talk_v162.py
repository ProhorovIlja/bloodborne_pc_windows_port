#!/usr/bin/env python3
"""V162 source-exact YT #468/#471 guest Doll end transition for pinned YT1.3.

Original game V151 + V160 contain only selected reviewed #457/#468 hunks;
they are not identical to #468 tip. Therefore a blind b18..a642 Git patch
will not apply. Transplant only exact semantic Doll functions/blocks directly
from reviewed #471, validating original and reviewed Git blobs first.

Never touches game assets, server protocol, saves, native launcher or live players.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import stage_doll_own_flag_v151 as donor151
import stage_doll_second_levelup_v160 as donor160

ORIGINAL="0645740a33ae21c56df3b4a0d9777086dbca6053"
PREVIOUS="b18c5f371a19ca9a605e8fc40f8a57876ed12aac"
MIDDLE="a64214d4875ff7cbe735b155e8b075261891e1cc"
REVIEWED="4a55f02c48207770273e0cf0ed5d06e85a9143e5"
ROOT="emulator/"
FILES={
 "src/core/bloodborne_party.cpp":("5186b4ed9fa9387752f4dc21362950d70d062505","b1b13cb0063188231b932e64bb66efa26644330d"),
 "src/core/bloodborne_party.h":("dc42d0509461fda6f557fa88f98a29fa28d877af","8aecb1153a88ea20bbf6de4bfa2f06bcdeb26705"),
 "src/core/bloodborne_travel.cpp":("cf8112da1c9f897cdeb254d8f592edf12e74e57f","487c3f0197eeb69a4549deac1cf698cffe994ebc"),
 "tests/bloodborne/test_bloodborne_flag_rules.cpp":("5adbed2977d43efbdde41051c8e41060464c2301","0cf8e08e1ddda34c77eb776e9cbe5d203a8eb512"),
}
CPP="src/core/bloodborne_party.cpp"
HEADER="src/core/bloodborne_party.h"
TRAVEL="src/core/bloodborne_travel.cpp"
TEST="tests/bloodborne/test_bloodborne_flag_rules.cpp"
CPP_START="bool BeginsDollBlessing(bool level_up_on) {\n"
CPP_END="\nstd::vector<s32> LightRequestsToClear("
HEADER_START="// The 1.3.1 rig 2026-10-30: after 72100100 her talk (state 10)"
HEADER_END="// The other player's \"set this event flag\""
HOOK_START="    // See ClearsDollLevelUpFlagOnHerBlessing: cleared by the next tick\n"
HOOK_END="    // An NPC's gift (common event 9100 ends for a phantom)"
TICK_START="// See ClearsDollLevelUpFlagAfterHerMenu: every frame in a party (her blessing can be over within a\n"
TICK_END="// See ImpurityBonusChange: every second, the Impurity rune's HP bonus put on"
TALK_START="void PS4_SYSV_ABI NoteTalkCommand(u64, GuestRegisterSnapshot* registers) {\n"
TALK_END="    if (!esd_answers_wanted.load(std::memory_order_relaxed)) {\n"
TEST_START="// The 1.3.1 rig 2026-10-30 (doll-level-up-twice"
TEST_END="// Kaniel 2026-10-30: the host's level up played the kneel on guests."
TICK_OLD="    KeepHeadstoneFlagsOwn();\n    ClearDollLevelUpFlagAfterHerMenu();\n"
TICK_NEW=(
"    KeepHeadstoneFlagsOwn();\n"
"    const bool blessing_begun = doll_blessing_asked.exchange(false);\n"
"    ClearDollLevelUpFlagAfterHerMenu(blessing_begun);\n"
"    FinishGuestDollBlessing(blessing_begun, doll_blessing_end_asked.exchange(false));\n"
)

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],
                                   text=True,stderr=subprocess.DEVNULL).strip()

def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()

def region(text,start,end,label):
    if text.count(start)!=1:
        raise ValueError("V162 reviewed upstream start marker drift: "+label)
    at=text.index(start)
    stop=text.find(end,at+len(start))
    if stop<0:
        raise ValueError("V162 reviewed upstream end marker drift: "+label)
    return text[at:stop]

def one(text,old,new,label):
    if old==new or text.count(old)!=1 or new in text:
        raise ValueError("V162 pinned original staged hunk drift: "+label)
    return text.replace(old,new,1)

def patch(name,base,prior,reviewed,middle):
    if name not in FILES or "ClearsDollLevelUpFlagOnHerBlessing" not in base or (
            "EndsDollBlessing" in base or "BeginsDollBlessing" in base):
        raise ValueError("V162 requires original V151+V160, not #468 whole source")
    if name==CPP:
        new=region(reviewed,CPP_START,CPP_END,"C++ helper trio")
        if ("bool EndsDollBlessing(s32 talk_command)" not in new or
                "return talk_command == 71;" not in new or
                "std::optional<bool> DollBlessingStepFor(" not in new or
                len(new)>1000 or CPP_START not in middle or
                "bool EndsDollBlessing(" in middle):
            raise ValueError("V162 helper dependency/source review drift")
        return one(base,CPP_END,"\n"+new+CPP_END,"full Doll helper trio")
    if name==HEADER:
        new=region(reviewed,HEADER_START,HEADER_END,"header pair steps and end")
        if ("DollBlessingSteps" not in new or "bool EndsDollBlessing(" not in new or
                len(new)>1800):
            raise ValueError("V162 header review drift")
        return one(base,HEADER_END,new+HEADER_END,"own guest step declarations")
    if name==TRAVEL:
        base=one(base,"std::atomic<bool> doll_blessing_asked{};\n",
                 "std::atomic<bool> doll_blessing_asked{};\n"
                 "std::atomic<bool> doll_blessing_end_asked{};\n","end request atomic")
        old=region(prior,HOOK_START,HOOK_END,"V160 reviewed hook")
        new=region(reviewed,HOOK_START,HOOK_END,"V162 reviewed hook")
        if (old==new or "std::ranges::any_of(OtherPlayers()" not in new or
                "BeginsDollBlessing(" not in new or
                "doll_blessing_end_asked" not in new or len(new)>1300):
            raise ValueError("V162 guest own-talk hook semantic drift")
        base=one(base,old,new,"guest vs others own talk")
        new=region(reviewed,TALK_START,TALK_END,"talk-command 71 hook")
        if ("EndsDollBlessing(" not in new or
                "doll_blessing_end_asked.store(true)" not in new or len(new)>550):
            raise ValueError("V162 game talk end hook drift")
        base=one(base,TALK_START,new,"Doll talk command end")
        old=region(base,TICK_START,TICK_END,"staged V160 next tick")
        new=region(reviewed,TICK_START,TICK_END,"reviewed guest step finish")
        if ("void FinishGuestDollBlessing(bool begin_asked, bool end_asked)" not in new or
                "DollBlessingStepFor(" not in new or
                "PartyGhostSetEventFlagOffset" not in new or len(new)>2800):
            raise ValueError("V162 guest step/broadcast logic drift")
        base=one(base,old,new,"complete host/guest tick handlers")
        if TICK_NEW not in reviewed:
            raise ValueError("V162 expected reviewed per-frame call drift")
        return one(base,TICK_OLD,TICK_NEW,"per-frame begin/end atomic consumption")
    if name==TEST:
        new=region(reviewed,TEST_START,TEST_END,"reviewed original native gtest")
        if (len(new)>2600 or
                "TEST(BloodborneFlagRules, AGuestsDollBlessingFinishesWithoutTheKneelEvents)" not in new or
                "EXPECT_TRUE(EndsDollBlessing(71));" not in new or
                "DollBlessingStepFor(true, true, false, false)" not in new):
            raise ValueError("V162 reviewed original game regression drift")
        return one(base,TEST_END,new+TEST_END,"real native game regression")
    raise ValueError("V162 unrelated native game source refused")

def verify_staged(name,staged,reviewed):
    """All transplanted native C++/gtest function regions match exact #471."""
    pairs={
        CPP:((CPP_START,CPP_END),),
        HEADER:((HEADER_START,HEADER_END),),
        TRAVEL:((HOOK_START,HOOK_END),
                (TALK_START,TALK_END),
                (TICK_START,TICK_END)),
        TEST:((TEST_START,TEST_END),),
    }
    if name not in pairs:
        raise ValueError("V162 unexpected verification path")
    for start,end in pairs[name]:
        actual=region(staged,start,end,"staged "+name)
        expected=region(reviewed,start,end,"reviewed "+name)
        if actual != expected:
            raise ValueError("V162 assembled original native code differs from reviewed upstream #471: "+name)
    if name==TRAVEL and (TICK_OLD in staged or TICK_NEW not in staged):
        raise ValueError("V162 original game calls old Doll tick or omits begin/end consumption")

def check_original_stage(name,actual,original,donor151_text,donor160_text):
    """Fail closed if ANY byte outside the reviewed V151+V160 hunks drifted."""
    full_path=ROOT+name
    expected_151=donor151.apply(full_path,original,donor151_text)
    expected_160=donor160.patch(full_path,expected_151,donor160_text)
    if actual!=expected_160:
        raise ValueError("V162 full original working tree differs from exact V151+V160 source: "+full_path)

def stage(original,donor151_root,prior,middle,reviewed):
    original,donor151_root,prior,middle,reviewed=(x.resolve(strict=True)
                                    for x in (original,donor151_root,prior,middle,reviewed))
    if (git(original,"rev-parse","HEAD")!=ORIGINAL or
            git(donor151_root,"rev-parse","HEAD")!=donor151.REVIEWED_PIN or
            git(prior,"rev-parse","HEAD")!=PREVIOUS or
            git(middle,"rev-parse","HEAD")!=MIDDLE or
            git(reviewed,"rev-parse","HEAD")!=REVIEWED):
        raise ValueError("V162 original/prior/intermediate/reviewed Git revision changed")
    candidates=[]
    for name,(original_sha,reviewed_sha) in FILES.items():
        file=ROOT+name
        dst,src=original/file,reviewed/file
        if (not dst.is_file() or dst.is_symlink() or
                not src.is_file() or src.is_symlink() or
                git(original,"rev-parse","HEAD:"+file)!=original_sha or
                git(reviewed,"rev-parse","HEAD:"+file)!=reviewed_sha):
            raise ValueError("V162 exact Git-tracked original/reviewed blob mismatch: "+file)
        reviewed_bytes=src.read_bytes().replace(b"\r\n",b"\n")
        if blob(reviewed_bytes)!=reviewed_sha:
            raise ValueError("V162 reviewed file bytes differ from pinned Git blob: "+file)
        # Verify the complete staged bytes, not just our four fragments.
        # Original Git HEAD is pinned and must not be substituted with a
        # modified index/worktree as the baseline for source correctness.
        pristine=subprocess.check_output(
            ["git","-C",str(original),"show","HEAD:"+file])
        pristine=pristine.replace(b"\r\n",b"\n")
        if blob(pristine)!=original_sha:
            raise ValueError("V162 Git HEAD original native file bytes drift: "+file)
        donor151_path=donor151_root/file
        prior_path=prior/file
        if (not donor151_path.is_file() or donor151_path.is_symlink() or
                not prior_path.is_file() or prior_path.is_symlink() or
                git(donor151_root,"rev-parse","HEAD:"+file)!=donor151.FILES[file][1] or
                git(prior,"rev-parse","HEAD:"+file)!=donor160.FILES[file][1]):
            raise ValueError("V162 previous donor Git blobs missing or changed: "+file)
        donor151_bytes=donor151_path.read_bytes().replace(b"\r\n",b"\n")
        prior_bytes=prior_path.read_bytes().replace(b"\r\n",b"\n")
        if (blob(donor151_bytes)!=donor151.FILES[file][1] or
                blob(prior_bytes)!=donor160.FILES[file][1]):
            raise ValueError("V162 previous donor working tree bytes drift: "+file)
        base=dst.read_bytes().replace(b"\r\n",b"\n").decode("utf-8")
        prior_text=prior_bytes.decode("utf-8")
        check_original_stage(name,base,pristine.decode("utf-8"),
                             donor151_bytes.decode("utf-8"),prior_text)
        middle_text=(middle/file).read_text(encoding="utf-8")
        reviewed_text=reviewed_bytes.decode("utf-8")
        new=patch(name,base,prior_text,reviewed_text,middle_text)
        verify_staged(name,new,reviewed_text)
        candidates.append((dst,new.encode("utf-8")))
    # Validate four independently pinned source/target files before any write.
    for dst,data in candidates:
        dst.write_bytes(data)
    subprocess.run(["git","-C",str(original),"diff","--check"],check=True)
    print("SHYT_V162_EXACT_ORIGINAL_DOLL_GUEST_TALK_BEGIN_END_STAGED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("original","donor151","prior","middle","reviewed"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    stage(a.original,a.donor151,a.prior,a.middle,a.reviewed)
