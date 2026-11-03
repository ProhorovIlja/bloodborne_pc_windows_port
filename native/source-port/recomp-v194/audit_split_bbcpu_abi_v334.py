#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V334: inspect the November 2026 upstream CPU/recompiler repository split.

bloodborne-native/bloodborne-recomp moved its CPU runtime to
bloodborne-native/bbcpu. The latest recomp repo no longer contains
src/cpu/cpu_internal.h and src/recomp/rc.h; a prior frozen version
still carries both. This is an exact PUBLIC pinned source check.
Compare the old native Win64-host ABI to the actual standalone bbcpu
headers; do not mistake a renamed source comment for an ABI break.
This tests public headers only. It does NOT build proprietary game code.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

RECOMP_PIN="222db5101170135c8ee854bcf338237477bf4ae9"
BBCPU_PIN="3f9b6c1a11d5a443ee2e556a0d1f3aec4a73f0ca"
# Direct source blobs verified against GitHub: original and split runtime.
CPU_BLOB="bcbd422f92a84087a2e0c2d260ec64040f381540"
RC_OLD="a27b8f5fc872c75bd08f6788d716b6856c9e2309"
RC_BBCPU="20989474d1b863b2a486912d76fc09b209fb66d0"
FILES=("src/cpu/cpu_internal.h","src/recomp/rc.h")

def git(root:Path,*args:str)->str:
    p=subprocess.run(["git","-C",str(root),*args],
                     capture_output=True,text=True,timeout=12)
    if p.returncode:
        raise ValueError("unverified public source checkout")
    return p.stdout.strip()

def pinned_blob(root:Path,rel:str,sha:str)->str:
    path=root/rel
    if (not path.is_file() or path.is_symlink() or
            git(root,"rev-parse","HEAD:"+rel)!=sha or
            git(root,"hash-object",rel)!=sha):
        raise ValueError("unexpected split public ABI blob")
    return path.read_text(encoding="utf-8")

def verify(old:Path,new:Path)->None:
    old=old.resolve(strict=True)
    new=new.resolve(strict=True)
    if old==new or git(old,"rev-parse","HEAD")!=RECOMP_PIN or (
            git(new,"rev-parse","HEAD")!=BBCPU_PIN):
        raise ValueError("old recompiler and new CPU pins not satisfied")
    old_cpu=pinned_blob(old,FILES[0],CPU_BLOB)
    new_cpu=pinned_blob(new,FILES[0],CPU_BLOB)
    old_rc=pinned_blob(old,FILES[1],RC_OLD)
    new_rc=pinned_blob(new,FILES[1],RC_BBCPU)
    if old_cpu!=new_cpu:
        raise ValueError("split bbcpu changed the original guest CPU layout")
    # The ONLY difference here is the first documentation line:
    # the new file names "bloodborne-recomp's docs". No ABI changes.
    if (old_rc.splitlines(keepends=True)[1:]!=
            new_rc.splitlines(keepends=True)[1:]):
        raise ValueError("split bbcpu changed RcApi or generated functions")
    for text in (old_rc,new_rc):
        if ('#define BB_RECOMP_API_VERSION 4u' not in text or
            '#define BB_RECOMP_INIT "bb_recomp_init"' not in text or
            'typedef const RcFunction *(*RcInit)' not in text):
            raise ValueError("required native recomp initialization ABI missing")

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--old-recompiler",required=True,type=Path)
    p.add_argument("--split-bbcpu",required=True,type=Path)
    args=p.parse_args()
    try:verify(args.old_recompiler,args.split_bbcpu)
    except (ValueError,OSError,subprocess.TimeoutExpired):
        raise SystemExit("SHYT_V334_PUBLIC_SPLIT_RECOMPILER_ABI_REFUSED") from None
    print("SHYT_V334_PUBLIC_BBCPU_SPLIT_OLD_WINDOWS_AOT_ABI_SEMANTICALLY_UNCHANGED_PASS")

if __name__=="__main__":
    main()
