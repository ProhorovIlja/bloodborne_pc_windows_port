#!/usr/bin/env python3
"""V394: verify genuine ELF generated C object includes RcApi CALL RAX function.

Extends V393 symbol/relocation gate to exactly SIX fully emitted bbrecomp
function definitions. Host RcApi.call is a function POINTER via a
registered table, so its absence in undefined symbols is expected.
Source inspection of the exact pinned f_10a0 body is required as well.
This is NOT a proof of all native memory accesses or full game import
closure; no original retail files are read.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import re
import shutil
import subprocess
import sys

P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v393_object",P/"verify_generated_object_v393.py")
if spec is None or spec.loader is None:
    raise RuntimeError("missing V393 object gate")
original=importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
FUNCTIONS=("f_1000","f_1020","f_1040","f_1060","f_1080","f_10a0")

def verify_call_source(original_c:str,patched_c:str)->None:
    v390spec=importlib.util.spec_from_file_location("v390instrument",
        P/"instrument_generated_aot_memory_v390.py")
    if v390spec is None or v390spec.loader is None:
        raise ValueError("missing pinned original-source instrumenter")
    v390=importlib.util.module_from_spec(v390spec)
    v390spec.loader.exec_module(v390)
    expected,_=v390.transform(original_c)
    if expected!=patched_c:
        raise ValueError("compiled shard not exact instrumented pinned source")
    match=re.search(
        r"\bvoid\s+f_10a0\s*\(\s*BbCpu\s*\*\s*c\s*\)\s*\{",
        original_c)
    if not match:
        raise ValueError("missing real generated CALL RAX function body")
    next_function=re.search(r"\bvoid\s+f_[0-9a-f]+\s*\(",original_c[match.end():])
    part=original_c[match.start():match.end()+(next_function.start() if next_function else len(original_c)-match.end())]
    if not re.search(r"\brc->call\s*\(\s*c\s*,",part):
        raise ValueError("actual compiler f_10a0 did not route guest call to RcApi.call")
    if re.search(r"\brc->step\s*\(",part):
        raise ValueError("generated guest host call falls back to interpreter")

def verify_object(obj:Path)->None:
    if obj.is_symlink() or obj.suffix!=".o" or (
        not obj.is_file()) or obj.stat().st_size>10_000_000:
        raise ValueError("not an original-free bounded ELF .o")
    nm=shutil.which("nm")
    objdump=shutil.which("objdump")
    if not nm or not objdump:
        raise ValueError("Linux binutils required")
    orig=original.FUNCTIONS
    try:
        original.FUNCTIONS=FUNCTIONS
        original.verify_symbols(
            original.subprocess_output([nm,"--undefined-only",str(obj)]),
            original.subprocess_output([nm,"--defined-only",str(obj)]),
            original.subprocess_output([objdump,"-r",str(obj)]))
    finally:
        original.FUNCTIONS=orig

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--object",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--patched",type=Path,required=True)
    a=p.parse_args()
    for path in (a.source,a.patched):
        if not path.is_file() or path.is_symlink() or path.stat().st_size>2_000_000:
            raise ValueError("source not original-free, regular, bounded generated C")
    verify_call_source(a.source.read_text(encoding="utf-8"),
                       a.patched.read_text(encoding="utf-8"))
    verify_object(a.object)
    print("NATIVE_V394_REAL_GENERATED_CALL_RAX_ELF_OBJECT_ROUTING_PASS")
    print("generated_functions=6 compiled_host_callback_route=TRUE")
    print("original_Bloodborne_game_boot_proven=FALSE")

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,UnicodeError,subprocess.TimeoutExpired) as e:
        print("NATIVE_V394_GENERATED_CALL_AUDIT_REFUSED: "+
              type(e).__name__,file=sys.stderr)
        raise SystemExit(2)
