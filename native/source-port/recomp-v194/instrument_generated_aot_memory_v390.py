#!/usr/bin/env python3
"""V390: fail-closed memory-call remap in ACTUAL pinned bbrecomp generated C.

Only source-locked public original bbrecomp generated SHARD bodies. Does not
touch upstream rc.h, and never prints or publishes owner-private generated C.
This is NOT automatic interception of arbitrary raw C pointers. Original
game's full generated-code audit and guest syscall/import closure are P0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

PINNED="8f31ec7c41f252730c6325d52647046baef7549f"
GENERATOR_BLOB="f5032c9ead4988579e005af8a0a0ce4ba4ab66d8"
INCLUDE='#include "recomp/rc.h"'
INJECTION='#include "native_generated_memory_calls_v390.h"'
CALLS=("rc_ld","rc_lds","rc_st","rc_sts","rc_cas","rc_vld","rc_vst")
DANGEROUS=("bb_load","bb_store","bb_fence_load","bb_fence_store")
MAX_SOURCE=20_000_000


def git_blob(payload:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(payload)).encode()+b"\0"+payload).hexdigest()


def verify_generator(path:Path)->None:
    root=path.resolve(strict=True)
    rev=subprocess.check_output(
        ["git","-C",str(root),"rev-parse","HEAD"],
        stderr=subprocess.DEVNULL,text=True).strip()
    if rev!=PINNED:
        raise ValueError("pinned bbrecomp upstream revision mismatch")
    source=subprocess.check_output(
        ["git","-C",str(root),"show","HEAD:tools/recomp/bbrecomp.c"],
        stderr=subprocess.DEVNULL)
    if git_blob(source)!=GENERATOR_BLOB:
        raise ValueError("pinned bbrecomp generator blob mismatch")


def transform(source:str,require_scalar:bool=False)->tuple[str,dict[str,int]]:
    if source.count(INCLUDE)!=1 or INJECTION in source:
        raise ValueError("expected exactly one unmodified real RcApi include")
    if len(source.encode("utf-8"))>MAX_SOURCE:
        raise ValueError("generated source exceeds bounded instrumentation size")
    if not re.search(r"\bvoid\s+[A-Za-z_]\w*\s*\(\s*BbCpu\s*\*\s*\w+\s*\)\s*\{",source):
        raise ValueError("not a generated RcFunction body shard")
    if any(re.search(r"\b"+x+r"\s*\(",source) for x in DANGEROUS):
        raise ValueError("unmediated host-pointer memory helper detected")
    counts={x:len(re.findall(r"\b"+x+r"\s*\(",source)) for x in CALLS}
    if sum(counts.values())==0:
        raise ValueError("generated body contains no supported guest memory operation")
    if require_scalar and not (counts["rc_ld"]+counts["rc_lds"] and
                              counts["rc_st"]+counts["rc_sts"]):
        raise ValueError("expected real generated scalar guest load and store")
    result=source.replace(INCLUDE,INCLUDE+"\n"+INJECTION,1)
    if result.count(INJECTION)!=1:
        raise ValueError("V390 instrumentation was not inserted exactly once")
    return result,counts


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--require-scalar",action="store_true")
    a=p.parse_args()
    verify_generator(a.upstream_checkout)
    source=a.source.resolve(strict=True)
    target=a.output.absolute()
    if not source.is_file() or a.source.is_symlink() or target.exists() or        not target.parent.is_dir() or target.parent.is_symlink() or        source==target or source.suffix!=".c" or target.suffix!=".c":
        raise ValueError("requires fresh independent .c output inside existing temp directory")
    if source.stat().st_size>MAX_SOURCE:
        raise ValueError("input generated shard too large")
    transformed,counts=transform(source.read_text(encoding="utf-8"),
                                 a.require_scalar)
    target.write_text(transformed,encoding="utf-8")
    # No generated code content, private game bytes, original addresses,
    # or filenames are returned by this bounded tool.
    print("NATIVE_V390_PINNED_GENERATED_AOT_MEMORY_CALL_INSTRUMENTATION_PASS")
    print(json.dumps({"helper_counts":counts,
                      "guest_runtime_elf_required":False,
                      "original_bloodborne_game_boot_proven":False},
                      sort_keys=True))
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,subprocess.CalledProcessError,
            UnicodeError) as exc:
        print("V390_MEMORY_INSTRUMENTATION_REFUSED: "+
              type(exc).__name__,file=sys.stderr)
        raise SystemExit(2)
