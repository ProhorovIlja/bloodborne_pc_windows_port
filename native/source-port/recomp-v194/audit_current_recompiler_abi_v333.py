#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V333: check updated public upstream AOT CPU/host callback ABI.

The native Windows host is intentionally source-pinned to an older
bloodborne-native/bloodborne-recomp revision. This independent read-only
check confirms the most recent vetted public upstream still has EXACT
same CPU layout and RcApi contract, before moving source-generation
toolchains. It never reads, uploads, copies or links original game files.
This is an ABI checkpoint, not proof of a working game runtime.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

LATEST_PUBLIC="222db5101170135c8ee854bcf338237477bf4ae9"
OLD_PUBLIC="8f31ec7c41f252730c6325d52647046baef7549f"
EXPECTED={
    "src/cpu/cpu_internal.h":"bcbd422f92a84087a2e0c2d260ec64040f381540",
    "src/recomp/rc.h":"a27b8f5fc872c75bd08f6788d716b6856c9e2309",
}
def git(root:Path,*cmd:str)->str:
    result=subprocess.run(["git","-C",str(root),*cmd],
                          capture_output=True,text=True,timeout=12)
    if result.returncode:raise ValueError("unverified public upstream")
    return result.stdout.strip()

def verified(root:Path)->None:
    if not root.is_dir() or root.is_symlink() or (
        git(root,"rev-parse","HEAD")!=LATEST_PUBLIC):
        raise ValueError("wrong public upstream commit")
    for path,expected in EXPECTED.items():
        target=root/path
        if not target.is_file() or target.is_symlink() or (
            git(root,"rev-parse","HEAD:"+path)!=expected or
            git(root,"hash-object",path)!=expected):
            raise ValueError("public upstream ABI source drift")
    rc=(root/"src/recomp/rc.h").read_text(encoding="utf-8")
    if ("#define BB_RECOMP_API_VERSION 4u" not in rc or
        '#define BB_RECOMP_INIT "bb_recomp_init"' not in rc):
        raise ValueError("original generated-function ABI changed")

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream",type=Path,required=True)
    args=parser.parse_args()
    verified(args.upstream.resolve(strict=True))
    print("SHYT_V333_NEW_PUBLIC_UPSTREAM_CPU_AND_RC_API_ABI_UNCHANGED_PASS")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:
        raise SystemExit("V333 refused upstream ABI change: "+
                         type(error).__name__) from None
