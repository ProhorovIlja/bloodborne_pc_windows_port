#!/usr/bin/env python3
"""Build and execute ORIGINAL source-locked upstream rc.h helper C on Win64.

Use an empty Zydis include placeholder only because the *header itself*
does not use any Zydis types. This cannot be used to build a full game:
actual bbrecomp/decoder needs real Zydis. Does NOT touch or read game dumps.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"upstream_rc_probe_v195.c"
PIN_MARK="SHYT_NATIVE_V195_WIN32_MONOTONIC_GUEST_TSC"

def call(args, phase:str)->None:
    result=subprocess.run(args,capture_output=True,text=True,timeout=90)
    if result.returncode:
        excerpt="\n".join((result.stderr or result.stdout).splitlines()[-12:])
        raise RuntimeError(phase+" failed: "+excerpt[:3000])

def run(root:Path)->None:
    root=root.resolve(strict=True)
    header=root/"src/recomp/rc.h"
    original=root/"src/cpu/cpu_internal.h"
    if (not header.is_file() or not original.is_file() or
        header.is_symlink() or original.is_symlink() or
        header.read_text(encoding="utf-8").count(PIN_MARK)!=1):
        raise ValueError("V195 exact upstream header patch not staged")
    with tempfile.TemporaryDirectory(prefix="v195-public-rc-") as tmp:
        root_out=Path(tmp)
        inc=root_out/"inc"/"Zydis"
        inc.mkdir(parents=True)
        # This is deliberately NOT a real Zydis implementation. Only the
        # RcApi inline-helper compilation is checked; production requires
        # the real, correctly pinned Zydis dependency.
        (inc/"Zydis.h").write_text("/* empty synthetic include-only header */\n")
        exe=root_out/("upstream-rc-probe.exe" if sys.platform=="win32" else "upstream-rc-probe")
        if sys.platform=="win32":
            compiler=shutil.which("clang-cl")
            if not compiler:raise RuntimeError("clang-cl not available")
            command=[compiler,"/nologo","/std:c11","/O2","/W3",
                     "/I"+str(root/"src"),"/I"+str(root_out/"inc"),
                     "/Fe"+str(exe),str(SOURCE),"/link","kernel32.lib"]
        else:
            compiler=shutil.which("clang") or shutil.which("cc")
            if not compiler:raise RuntimeError("native C compiler unavailable")
            command=[compiler,"-std=c11","-O2","-D_POSIX_C_SOURCE=200809L",
                     "-Wall","-Wextra","-Werror","-I",str(root/"src"),
                     "-I",str(root_out/"inc"),str(SOURCE),"-o",str(exe)]
        call(command,"original public upstream header native compiler")
        call([str(exe)],"original public upstream helper execution")
    print("SHYT_V195_ORIGINAL_UPSTREAM_RC_H_PLATFORM_NATIVE_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    a=p.parse_args()
    run(a.upstream_checkout)
