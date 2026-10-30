#!/usr/bin/env python3
"""V162: pin YT #471's guest Doll begin/end repair on staged V151+V160.

Developer-only native original YT1.3 source. No game files, server, wire,
launcher, or production changes. Requires original YT1.3 + exact reviewed #471.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

ORIGINAL = "0645740a33ae21c56df3b4a0d9777086dbca6053"
REVIEWED = "4a55f02c48207770273e0cf0ed5d06e85a9143e5"
PREVIOUS = "b18c5f371a19ca9a605e8fc40f8a57876ed12aac"
MIDDLE = "a64214d4875ff7cbe735b155e8b075261891e1cc"
ROOT = "emulator/"
FILES = {
    "src/core/bloodborne_party.cpp": ("5186b4ed9fa9387752f4dc21362950d70d062505", "b1b13cb0063188231b932e64bb66efa26644330d"),
    "src/core/bloodborne_party.h": ("dc42d0509461fda6f557fa88f98a29fa28d877af", "8aecb1153a88ea20bbf6de4bfa2f06bcdeb26705"),
    "src/core/bloodborne_travel.cpp": ("cf8112da1c9f897cdeb254d8f592edf12e74e57f", "487c3f0197eeb69a4549deac1cf698cffe994ebc"),
    "tests/bloodborne/test_bloodborne_flag_rules.cpp": ("5adbed2977d43efbdde41051c8e41060464c2301", "0cf8e08e1ddda34c77eb776e9cbe5d203a8eb512"),
}
PATCHES = {
 "src/core/bloodborne_party.cpp": (
    "bool BeginsDollBlessing(bool level_up_on) {\n    return level_up_on;\n}\n\n",
    "bool BeginsDollBlessing(bool level_up_on) {\n    return level_up_on;\n}\n\n"
    "bool EndsDollBlessing(s32 talk_command) {\n    return talk_command == 71;\n}\n\n"),
 "src/core/bloodborne_party.h": (
    "bool BeginsDollBlessing(bool level_up_on);\n",
    "bool BeginsDollBlessing(bool level_up_on);\n"
    "// Her state 6 runs talk command 71 (the talk-ended notice) right before state 11; the rig showed\n"
    "// state 11's request for 72100100 never reached the flag hook, so command 71 ends her blessing.\n"
    "bool EndsDollBlessing(s32 talk_command);\n"),
 "src/core/bloodborne_travel.cpp": (
    "    if (ClearsDollLevelUpFlagOnHerBlessing(party_controller.has_value(),\n"
    "                                           esd_talker >= 0x10000 && esd_talker != GetLocalPlayer(),\n"
    "                                           flag)) {\n",
    "    // The talker is the Doll here, not a player: another player's talk is one of theirs.\n"
    "    if (ClearsDollLevelUpFlagOnHerBlessing(\n"
    "            party_controller.has_value(),\n"
    "            esd_talker >= 0x10000 && std::ranges::any_of(OtherPlayers(),\n"
    "                                                         [](const OtherPlayer& other) {\n"
    "                                                             return other.character == esd_talker;\n"
    "                                                         }),\n"
    "            flag)) {\n"),
 "tests/bloodborne/test_bloodborne_flag_rules.cpp": (
    "    EXPECT_FALSE(BeginsDollBlessing(false)); // state 11 or her first choices (state 1)\n",
    "    EXPECT_FALSE(BeginsDollBlessing(false)); // state 11 or her first choices (state 1)\n"
    "    // The rig on a64214d: her state 11 request never reached the flag hook; state 6 runs talk\n"
    "    // command 71 (\"talk ended\") right before it.\n"
    "    EXPECT_TRUE(EndsDollBlessing(71));\n"
    "    EXPECT_FALSE(EndsDollBlessing(68)); // her menu\n"
    "    EXPECT_FALSE(EndsDollBlessing(31));\n"),
}
TALK_OLD = (
    "void PS4_SYSV_ABI NoteTalkCommand(u64, GuestRegisterSnapshot* registers) {\n"
    "    if (!esd_answers_wanted.load(std::memory_order_relaxed)) {\n")
TALK_NEW = (
    "void PS4_SYSV_ABI NoteTalkCommand(u64, GuestRegisterSnapshot* registers) {\n"
    "    // See EndsDollBlessing (only a guest's own blessing steps are ever put off by it).\n"
    "    if (EndsDollBlessing(static_cast<s32>(registers->rax))) {\n"
    "        doll_blessing_end_asked.store(true);\n"
    "    }\n"
    "    if (!esd_answers_wanted.load(std::memory_order_relaxed)) {\n")
def one(text, old, new, label):
    if text.count(old) != 1 or new in text:
        raise ValueError("V162 staged original Doll source drift: " + label)
    return text.replace(old, new, 1)

def patch(name, staged, reviewed):
    if (name not in PATCHES or
            "BeginsDollBlessing" not in staged or
            "ClearsDollLevelUpFlagOnHerBlessing" not in staged or
            "EndsDollBlessing" in staged):
        raise ValueError("V162 requires exact staged V151+V160 original Doll: " + name)
    old, new = PATCHES[name]
    # Some upstream additions retain the original prefix (party/header/test);
    # do not reject that exact retained context as if it were an old hunk.
    if reviewed.count(new) != 1 or new in staged:
        raise ValueError("V162 pinned upstream #471 content drift: " + name)
    out = one(staged, old, new, name)
    if name == "src/core/bloodborne_travel.cpp":
        if reviewed.count(TALK_NEW) != 1 or TALK_OLD in reviewed:
            raise ValueError("V162 reviewed talk command source drift")
        out = one(out, TALK_OLD, TALK_NEW, "talk command 71 end flag")
    return out

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   text=True, stderr=subprocess.DEVNULL).strip()

def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\x00" + data).hexdigest()

def stage(original, middle, reviewed):
    original, middle, reviewed = (p.resolve(strict=True) for p in (original, middle, reviewed))
    if (git(original, "rev-parse", "HEAD") != ORIGINAL or
            git(middle, "rev-parse", "HEAD") != MIDDLE or
            git(reviewed, "rev-parse", "HEAD") != REVIEWED or
            git(middle, "rev-parse", PREVIOUS) != PREVIOUS):
        raise ValueError("V162 original or intermediate/upstream reviewed commit mismatch")
    # Original V160 pins the FIRST #468 commit, which did not yet implement
    # DollBlessingStepFor begin/end. Apply exactly the two later #468 commits
    # before #471; using #471 by itself is a broken and unbuildable half-port.
    paths = [ROOT + name for name in FILES]
    delta = subprocess.check_output(
        ["git", "-C", str(middle), "diff", "--no-ext-diff", "--binary",
         PREVIOUS, MIDDLE, "--", *paths])
    changed_paths = git(middle, "diff", "--name-only", PREVIOUS, MIDDLE, "--", *paths).splitlines()
    if set(changed_paths) != set(paths) or not delta or b"Binary files" in delta:
        raise ValueError("V162 intermediate #468 changed-file scope mismatch")
    for args in (["--check", "-"], ["-"]):
        subprocess.run(["git", "-C", str(original), "apply", *args],
                       input=delta, check=True)
    changed = []
    for name, (original_blob, reviewed_blob) in FILES.items():
        path = ROOT + name
        target, source = original / path, reviewed / path
        if (not target.is_file() or target.is_symlink() or
                not source.is_file() or source.is_symlink() or
                git(original, "rev-parse", "HEAD:" + path) != original_blob or
                git(reviewed, "rev-parse", "HEAD:" + path) != reviewed_blob):
            raise ValueError("V162 original/reviewed tracked blob drift: " + path)
        src = source.read_bytes().replace(b"\r\n", b"\n")
        if blob(src) != reviewed_blob:
            raise ValueError("V162 reviewed raw content mismatch: " + path)
        base = target.read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
        out = patch(name, base, src.decode("utf-8"))
        changed.append((target, out.encode("utf-8")))
    # Fail closed: verify all four before touching any of them.
    for path, data in changed:
        path.write_bytes(data)
    subprocess.run(["git", "-C", str(original), "diff", "--check"], check=True)
    print("SHYT_V162_YT130_DOLL_GUEST_BEGIN_END_REVIEWED_CXX_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--middle", type=Path, required=True)
    parser.add_argument("--reviewed", type=Path, required=True)
    a = parser.parse_args()
    stage(a.original, a.middle, a.reviewed)
