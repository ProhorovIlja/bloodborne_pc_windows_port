#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V455: opt-in safety candidate; prevent BBHOST_GAME_FPS bypass of CLS co-op FPS ceiling.

The current CLS v1.4.0 BBHost FPS code returns immediately on BBHOST_GAME_FPS,
so 360/960/uncapped settings escape its documented 60/120 online limit.
Keep the original offline override, while online always clamps to the same
limit that the released CLS build already intends to enforce.

Apply only to a disposable, previously source-pinned V451 staged checkout.
No production mutation, no game files and no user save data.
"""
from __future__ import annotations
import argparse
import pathlib
from stage_cls_yt_bbhost_v451 import RELEASE_FRAME

CORRECTED = '''    int cap = host_settings().frame_cap;
    if (const char* e = std::getenv("BBHOST_GAME_FPS"); e && *e) cap = std::atoi(e);
    // BBSC: co-op plays at 60, or up to 120 unlocked: above that the others freeze and fly.
    // Apply the online ceiling AFTER all FPS overrides, including uncapped (0).
    if (const char* online = std::getenv("BB_ONLINE"); online && online[0] == '1') {
        const char* unlocked = std::getenv("BB_ONLINE_UNLOCKED_FPS");
        const int most = unlocked && unlocked[0] == '1' ? 120 : 60;
        if (cap <= 0 || cap > most) cap = most;
    }
    return mode_of(cap);
'''

def apply(text:str)->str:
    if text.count(RELEASE_FRAME)!=1:
        raise ValueError("expected exact CLS FPS seam missing or ambiguous; refuse")
    if text.count("int wanted_fps() {")!=1:
        raise ValueError("FPS entrypoint unexpectedly changed")
    return text.replace(RELEASE_FRAME,CORRECTED,1)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=pathlib.Path,required=True)
    p.add_argument("--apply",action="store_true")
    p.add_argument("--allow-candidate",action="store_true")
    a=p.parse_args()
    if not a.allow_candidate:
        raise SystemExit("SHYT_V455_CANDIDATE_EXPLICIT_OPT_IN_REQUIRED")
    if a.source.is_symlink() or not a.source.is_file():
        raise SystemExit("SHYT_V455_CANDIDATE_REFUSED_SOURCE")
    source=a.source.read_text(encoding="utf-8")
    result=apply(source)
    if a.apply:
        a.source.write_text(result,encoding="utf-8",newline="\n")
    print("SHYT_V455_CLS_ONLINE_FPS_OVERRIDE_SAFETY_"+("STAGED" if a.apply else "PINNED"))
    print("SHYT_V455_NO_GAME_BOOT_OR_PRODUCTION_PROMOTION")

if __name__=="__main__":
    main()
