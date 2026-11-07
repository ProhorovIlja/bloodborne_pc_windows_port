#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V452: authenticate and apply CLS's *real* YT v1.4.0 BBHost source patch.

Never mutates production nor the user-owned original game files. Source-only,
staged on disposable pinned YT checkout; does not build or run game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from compare_cls_bbhost_rebase_v450 import EXPECTED_ZIP, PREFIX

YT_COMMIT="efa0ad265d840d9195e55db2e3216f46f7daedd0"
PUBLIC_PATCH="yharnam-together-v1.4.0-bbhost.patch"
PATCH_SHA="0448e24e4c744d3825baef1356648c8638114b26b545e268edb3bf6de59c2c4f"
CHANGED=(
"bbport/gpu/shim/bbport_overlay.cpp",
"bbport/launcher/bbhost_options.py",
"bbport/launcher/bbhost_options_table.py",
"bbport/launcher/bbport_coop.py",
"bbport/launcher/bbport_launcher_win.py",
"emulator/src/core/bloodborne_patches.cpp",
)

def git(root:Path,*args:str,stdin:bytes|None=None)->str:
    p=subprocess.run(["git","-C",str(root),*args],input=stdin,
                     capture_output=True,timeout=25)
    if p.returncode:
        raise ValueError("pinned original YT BBHost patch rejected at "+args[0])
    return p.stdout.decode(errors="replace").strip()

def apply(archive:Path,source:Path)->dict:
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size>32*1024*1024:
        raise ValueError("unexpected source archive")
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=EXPECTED_ZIP:
            raise ValueError("CLS ZIP provenance mismatch")
    if git(source,"rev-parse","HEAD")!=YT_COMMIT or git(source,"status","--porcelain"):
        raise ValueError("YT original checkout must be clean and exact 1.4.0")
    with zipfile.ZipFile(archive) as z:
        patch=z.read(PREFIX+PUBLIC_PATCH)
    if len(patch)>65536 or hashlib.sha256(patch).hexdigest()!=PATCH_SHA:
        raise ValueError("CLS v1.4.0 YT source patch SHA mismatch")
    git(source,"apply","--check","-",stdin=patch)
    git(source,"apply","-",stdin=patch)
    if git(source,"diff","--check"):
        raise ValueError("bad whitespace in patch")
    results=git(source,"status","--short").splitlines()
    if len(results)<len(CHANGED):
        raise ValueError("YT source patch did not modify expected paths")
    for rel in CHANGED:
        if not (source/rel).is_file():
            raise ValueError("BBHost-original YT patch changed/missing required path")
    if "hle_thread_enter_guest" not in (source/CHANGED[-1]).read_text():
        raise ValueError("co-op guest thread initialization absent")
    if "BBSC_ON_BBHOST" not in (source/CHANGED[0]).read_text():
        raise ValueError("BBHost game/UI features missing")
    return {"schema":"SHYT_V452_CLS_BBHOST_YT140_ORIGINAL_SOURCE_PATCH",
            "yt_commit":YT_COMMIT,"release_sha256":EXPECTED_ZIP,
            "patch_sha256":PATCH_SHA,"changed":list(CHANGED),
            "proof_only":"source patch applies, not a running client, no YT→BBHost live NetSync"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--yt",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    a=p.parse_args()
    info=apply(a.archive,a.yt)
    a.report.write_text(json.dumps(info,indent=2)+"\n")
    print("SHYT_V452_ORIGINAL_CLS_YT_140_BBHOST_PATCH_APPLIED")
    print("SHYT_V452_CROSSSOURCE_GAMELINK_GUEST_THREAD_ENTER_PRESENT")
    print("SHYT_V452_READONLY_PRODUCTION_NO_GAME_FILES")

if __name__=="__main__":
    main()
