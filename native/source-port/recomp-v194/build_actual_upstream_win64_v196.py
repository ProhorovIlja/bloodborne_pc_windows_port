#!/usr/bin/env python3
"""Compile actual upstream bbrecomp-generated synthetic C into Win64 native EXE.

Python subprocess with absolute Windows paths avoids Git Bash/MSYS rewriting
clang-cl /I options. No guest ELF or EBOOT may be supplied, loaded or linked.
Only invented x86 instruction C generated in Linux CI is accepted here.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
HOST=HERE/"bbrecomp_generated_host_v196.c"
PROOF="SHYT_V196_ACTUAL_UPSTREAM_BBRECOMP_TO_NATIVE_WINDOWS_EXE_PASS"

def run(root:Path,artifact:Path,out:Path)->None:
    root=root.resolve(strict=True)
    artifact=artifact.resolve(strict=True)
    out=out.absolute()
    if out.suffix.lower()!=".exe" or out.is_symlink() or out.exists() or not out.parent.is_dir():
        raise ValueError("fresh native Windows EXE output path required")
    generated=artifact/"generated.c"
    include=artifact/"include"
    header=root/"src/recomp/rc.h"
    if not generated.is_file() or generated.is_symlink() or not header.is_file():
        raise ValueError("exact generated synthetic C or upstream RcApi header missing")
    if "SHYT_NATIVE_V195_WIN32_MONOTONIC_GUEST_TSC" not in header.read_text(encoding="utf-8"):
        raise ValueError("source-locked original Win32 runtime helper patch missing")
    if not (include/"Zydis/Zydis.h").is_file() or not (include/"Zycore/Defines.h").is_file():
        raise ValueError("real Zydis/Zycore 4.1.1 headers absent")
    source=generated.read_text(encoding="utf-8")
    if source.count("const RcFunction *bb_recomp_init(")!=1 or (
        sum("static void s_"+format(i,"x")+"(BbCpu *c)" in source
            for i in range(1,6))!=5
    ):
        raise ValueError("upstream-generated fixture not exact five native snippets")
    compiler=shutil.which("clang-cl")
    if not compiler:raise ValueError("clang-cl required for Win64 game AOT research")
    command=[compiler,"/nologo","/std:c11","/O2","/W0",
             "/I"+str((root/"src").resolve()),
             "/I"+str(include.resolve()),
             str(HOST.resolve()),str(generated.resolve()),
             "/Fe"+str(out),"/link","kernel32.lib"]
    built=subprocess.run(command,capture_output=True,text=True,timeout=120)
    if built.returncode:
        raise RuntimeError("native Win64 actual upstream-generated C failed to compile: "+
                           (built.stderr or built.stdout)[-2400:])
    result=subprocess.run([str(out)],capture_output=True,text=True,timeout=20)
    if result.returncode or PROOF not in result.stdout:
        raise RuntimeError("Win64 upstream C execution semantic oracle failed: "+
                           (result.stderr or result.stdout)[-1400:])
    reject=subprocess.run([str(out),"--eboot","forbidden"],capture_output=True,timeout=10)
    if reject.returncode==0:raise RuntimeError("native Win64 EXE accepted a runtime EBOOT argument")
    print(PROOF)
    print("No PS4 guest executable, runtime guest loader or proprietary game source.")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--synthetic-artifact",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.upstream_checkout,a.synthetic_artifact,a.out)
