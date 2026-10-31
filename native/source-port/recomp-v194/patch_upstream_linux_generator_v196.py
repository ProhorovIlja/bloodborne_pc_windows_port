#!/usr/bin/env python3
"""V196: enable full upstream bbcpu API on Linux for the *build-time* generator.

The original macOS-only conditional accidentally declares inline no-op stubs
on Linux, while its own original src/cpu/cpu.c provides those same functions.
This is a source-locked build-host fix, NOT guest CPU emulation in the final
native Windows executable. It edits ONLY the disposable upstream checkout.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess

UPSTREAM = "8f31ec7c41f252730c6325d52647046baef7549f"
HEADER = "src/cpu/bbcpu.h"
BLOB = "7cc2e3dc0f4a60da03ce933a533a7354c46ef9e3"
BEFORE = """#if defined(__APPLE__)
#define BB_HAVE_BBCPU 1
#endif
#ifdef BB_HAVE_BBCPU"""
AFTER = """#if defined(__APPLE__) || defined(__linux__)
/* SHYT_NATIVE_V196_BUILD_TIME_LINUX_BBCPU: full CPU source needed
 * by the offline bbrecomp generator, never linked into final Windows game.
 */
#define BB_HAVE_BBCPU 1
#endif
#ifdef BB_HAVE_BBCPU"""

def gitblob(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def stage(root:Path)->None:
    root=root.resolve(strict=True)
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                text=True,stderr=subprocess.DEVNULL).strip()
    if rev!=UPSTREAM:raise ValueError("V196 upstream compiler source revision drift")
    path=root/HEADER
    original=subprocess.check_output(["git","-C",str(root),"show","HEAD:"+HEADER])
    if gitblob(original)!=BLOB or not path.is_file() or path.is_symlink():
        raise ValueError("V196 exact original public CPU header changed")
    if path.read_text(encoding="utf-8")!=original.decode("utf-8"):
        raise ValueError("V196 build-host original source modified")
    source=original.decode("utf-8")
    if source.count(BEFORE)!=1 or AFTER in source:
        raise ValueError("V196 expected upstream host API conditional changed")
    build=root/"build.sh"
    original_build=subprocess.check_output(["git","-C",str(root),"show","HEAD:build.sh"])
    if gitblob(original_build)!="8f3ab76a4b5ae17bc496ad82d8eb3db1af4f3ff7":
        raise ValueError("V196 full original build driver source SHA drift")
    driver=original_build.decode("utf-8")
    old_flags="-Werror -Wno-unused-parameter"
    if driver.count(old_flags)!=1 or build.read_text(encoding="utf-8")!=driver:
        raise ValueError("V196 original build flags source drift")
    # Only silence a host-specific harmless warning; preserve -Werror for all
    # other diagnostics and compiler errors.
    driver=driver.replace(old_flags,
                          "-D_GNU_SOURCE -mcx16 -Werror -Wno-unused-function -Wno-atomic-alignment -Wno-unused-parameter",1)
    path.write_text(source.replace(BEFORE,AFTER,1),encoding="utf-8")
    build.write_text(driver,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_NATIVE_V196_LINUX_BUILD_HOST_BBCPU_SOURCE_PIN_PASS")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream-checkout",type=Path,required=True)
    stage(parser.parse_args().upstream_checkout)
