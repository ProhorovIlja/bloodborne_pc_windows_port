#!/usr/bin/env python3
"""Build complete ORIGINAL upstream bbrecomp whole-function output on Windows.

All source came from invented synthetic ELF. Native build/execution tests
guest RET and a true interprocedural direct CALL. No EBOOT at runtime.
"""
from pathlib import Path
import argparse
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
HOST=HERE/"bbrecomp_whole_function_host_v197.c"
PASS="SHYT_V197_ACTUAL_ORIGINAL_BBRECOMP_FUNCTION_CALL_RET_NATIVE_EXE_PASS"

def run(root:Path,artifact:Path,out:Path)->None:
    root=root.resolve(strict=True)
    artifact=artifact.resolve(strict=True)
    out=out.absolute()
    if out.suffix.lower()!=".exe" or out.exists() or out.is_symlink() or not out.parent.is_dir():
        raise ValueError("new Win64 .exe output required")
    files=(artifact/"recomp.c",artifact/"recomp_00000.c")
    if any(not f.is_file() or f.is_symlink() for f in files):
        raise ValueError("actual upstream whole-function C sources absent")
    main=files[0].read_text(encoding="utf-8")
    code=files[1].read_text(encoding="utf-8")
    for x in ("f_1000","f_1010","f_1020","f_1030","f_1050"):
        if "void "+x+"(BbCpu *c)" not in main or "void "+x+"(BbCpu *c)" not in code:
            raise ValueError("upstream real function missing: "+x)
    if "d_1050(c);" not in code or (
        "const RcFunction *bb_recomp_init(" not in main
    ):
        raise ValueError("real upstream CALL/direct dispatch table missing")
    if not (artifact/"include/Zydis/Zydis.h").is_file():
        raise ValueError("real Zydis headers missing")
    if not (root/"src/recomp/rc.h").is_file() or (
        "SHYT_NATIVE_V195_WIN32_MONOTONIC_GUEST_TSC"
        not in (root/"src/recomp/rc.h").read_text(encoding="utf-8")
    ):
        raise ValueError("source-locked original upstream Win32 RcApi absent")
    compiler=shutil.which("clang-cl")
    if not compiler:raise ValueError("clang-cl unavailable")
    cmd=[compiler,"/nologo","/std:c11","/O2","/W0",
         "/I"+str((root/"src").resolve()),
         "/I"+str((artifact/"include").resolve()),
         str(HOST.resolve()),*(str(f.resolve()) for f in files),
         "/Fe"+str(out),"/link","kernel32.lib"]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    if p.returncode:
        raise RuntimeError("real bbrecomp function C->native Win64 linker failed: "+
                           (p.stderr or p.stdout)[-2400:])
    result=subprocess.run([str(out)],capture_output=True,text=True,timeout=20)
    if result.returncode or PASS not in result.stdout:
        raise RuntimeError("real bbrecomp native whole-function test failed: "+
                           (result.stderr or result.stdout)[-1500:])
    negative=subprocess.run([str(out),"--eboot","not-allowed"],capture_output=True,timeout=20)
    if negative.returncode==0:
        raise RuntimeError("self-contained native Win64 function host accepted runtime EBOOT")
    print(PASS)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--synthetic-artifact",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.upstream_checkout,a.synthetic_artifact,a.out)
