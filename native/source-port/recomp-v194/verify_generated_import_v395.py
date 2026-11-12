#!/usr/bin/env python3
"""V395 exact source+ELF provenance for SEVEN actual pinned generated RcFn.

Two invented CALL RAX source sites must be separate function bodies:
 f_10a0 calls with generated next=0x4010a2 (allowed)
 f_10c0 calls with generated next=0x4010c2 (must be rejected by V395).
Source-locked ONLY; no private game bytes or original EBOOT at runtime.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "v394auditor",ROOT/"verify_generated_host_callback_v394.py")
if not spec or not spec.loader:raise RuntimeError("V394 audit missing")
v394=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v394)
FUNCTIONS=("f_1000","f_1020","f_1040","f_1060","f_1080","f_10a0","f_10c0")

def inspect_source(original:str,patched:str)->None:
    # V394 verifies original pinned f_10a0 and exact V390 insertion.
    v394.verify_call_source(original,patched)
    starts=list(re.finditer(
        r"\bvoid\s+(f_[0-9a-f]+)\s*\(\s*BbCpu\s*\*\s*c\s*\)\s*\{",
        original))
    matches=[i for i,m in enumerate(starts) if m.group(1)=="f_10c0"]
    if len(matches)!=1:
        raise ValueError("second generated x86 CALL site missing")
    idx=matches[0]
    start=starts[idx].start()
    end=starts[idx+1].start() if idx+1<len(starts) else len(original)
    body=original[start:end]
    if not re.search(r"\brc->call\s*\(\s*c\s*,",body):
        raise ValueError("second real generated call not RcApi.call")
    if re.search(r"\brc->(?:step|bail)\s*\(",body):
        raise ValueError("interpreter/bailout in generated call fixture")
    if not re.search(r"B\s*\+\s*0x10c2ull",body):
        raise ValueError("second guest CALL continuation was not actual 0x10c2")
    if original.count("void f_10c0(BbCpu *c) {")!=1:
        raise ValueError("duplicate 7th generated function")

def inspect_object(obj:Path)->None:
    prev=v394.FUNCTIONS
    try:
        v394.FUNCTIONS=FUNCTIONS
        v394.verify_object(obj)
    finally:
        v394.FUNCTIONS=prev

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--object",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--patched",type=Path,required=True)
    a=p.parse_args()
    for f in (a.source,a.patched):
        if f.is_symlink() or not f.is_file() or f.stat().st_size>2_000_000:
            raise ValueError("oversized or missing original-free generated C")
    inspect_source(a.source.read_text(encoding="utf-8"),
                   a.patched.read_text(encoding="utf-8"))
    inspect_object(a.object)
    print("NATIVE_V395_SEVEN_REAL_GENERATED_IMPORT_SITES_ELF_OBJECT_PASS")
    print("two_call_sites=TRUE; no_guest_interpreter=TRUE; original_game_boot=FALSE")
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,UnicodeError,RuntimeError) as e:
        print("NATIVE_V395_IMPORT_AUDIT_REFUSED: "+type(e).__name__,
              file=sys.stderr)
        raise SystemExit(2)
