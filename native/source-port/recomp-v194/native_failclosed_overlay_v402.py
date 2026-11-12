#!/usr/bin/env python3
"""V402: source-pinned fail-closed replacement for ALL general fallback exits.

The genuine upstream pinned bbrecomp emits a generic function epilogue
with rc->bail (guest translator continuation) and rc->tail (may delegate
back to guest runtime) even when native instructions are supported.

ONLY the separately generated eleven-function original-free fixture
can be transformed here, AFTER v390 memory instrumentation and the
V392 source-shard check. Known 'rc->bail(c, entry_rsp)' / 'rc->tail(c)'
callback sites are replaced with a C11 abort(); unknown callback
signatures, rc->step, rc->trace, pointer bypass, or extra code FAIL.
This is a "fail if unsupported", NOT complete native game semantics.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
SOURCE_NAME="recomp_00000_v390.c"
OUTPUT_NAME="recomp_00000_native_v402.c"
BAIL=re.compile(r"\brc\s*->\s*bail\s*\(\s*c\s*,\s*entry_rsp\s*\)")
TAIL=re.compile(r"\brc\s*->\s*tail\s*\(\s*c\s*\)")
GENERIC_FALLBACK=re.compile(r"\brc\s*->\s*(?:step|bail|tail|trace)\s*\(")
CALLBACK=re.compile(r"\brc\s*->\s*([a-zA-Z_]\w*)\s*\(")
EXACT_IMPORT=re.compile(r"\brc\s*->\s*call\s*\(")
BODY=re.compile(r"\bvoid\s+f_([0-9a-f]+)\s*\(\s*BbCpu\s*\*c\s*\)\s*\{")
INJECTION='#include "native_generated_memory_calls_v390.h"'
MARKER='#include <stdlib.h> /* V402 fail-closed only: abort unsupported transitions */'

def transform(source:str)->tuple[str,dict[str,int]]:
    if (len(source.encode("utf-8"))>2_000_000 or source.count(INJECTION)!=1 or
        MARKER in source or "rc->step(" in source or "rc->trace(" in source):
        raise ValueError("only previously instrumented native-only generated source permitted")
    functions=BODY.findall(source)
    if len(functions)!=11 or len(set(functions))!=11 or "1140" in functions:
        raise ValueError("not the eleven-function source-only native AOT closure")
    if set(int(x,16) for x in functions)!={0x1000,0x1020,0x1040,
        0x1060,0x1080,0x10a0,0x10c0,0x10e0,0x1100,0x1120,0x1160}:
        raise ValueError("missing/extra compiled function identity")
    callbacks=CALLBACK.findall(source)
    if set(callbacks)-{"call","bail","tail"}:
        raise ValueError("unexpected guest RcApi callback still present")
    if callbacks.count("call")!=2:
        raise ValueError("native import closure requires exactly two original CALL sites")
    bail=len(BAIL.findall(source))
    tail=len(TAIL.findall(source))
    if bail<11 or tail<11 or (bail!=callbacks.count("bail")) or (
        tail!=callbacks.count("tail")):
        raise ValueError("unrecognized bbcpu bailout/tail call form")
    compiled=BAIL.sub("abort()",source)
    compiled=TAIL.sub("abort()",compiled)
    if GENERIC_FALLBACK.search(compiled) or (
        EXACT_IMPORT.findall(compiled).__len__()!=2):
        raise ValueError("unmediated interpreter/translator or unaudited import")
    compiled=compiled.replace(INJECTION,INJECTION+"\n"+MARKER,1)
    if compiled.count(MARKER)!=1:
        raise ValueError("non-exact fail-closed compiler overlay")
    return compiled,{"functions":len(functions),"bail_abort":bail,
                     "tail_abort":tail,"source_imports":2}

def read_root(root:Path)->None:
    spec=importlib.util.spec_from_file_location(
        "v390_pinned",ROOT/"instrument_generated_aot_memory_v390.py")
    if not spec or not spec.loader:raise ValueError("V390 source locker missing")
    v390=importlib.util.module_from_spec(spec);spec.loader.exec_module(v390)
    v390.verify_generator(root)

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    read_root(a.upstream_checkout)
    if (a.source.is_symlink() or not a.source.is_file() or
        a.source.name!=SOURCE_NAME or a.source.stat().st_size>2_000_000 or
        a.out.name!=OUTPUT_NAME or a.out.exists() or
        not a.out.parent.is_dir() or a.out.parent.is_symlink() or
        a.source.parent!=a.out.parent or
        any((p/".git").exists()
            for p in (a.out.parent,*a.out.parent.parents))):
        raise ValueError("only one fresh runner-local original-free V390 shard allowed")
    text=a.source.read_text(encoding="utf-8")
    native,stats=transform(text)
    a.out.write_text(native,encoding="utf-8")
    print("NATIVE_V402_ALL_GUEST_TRANSLATOR_AND_TAIL_EXITS_ABORT_ONLY_PASS")
    print("invented_functions=11 transformed_bail="+str(stats["bail_abort"])+
          " transformed_tail="+str(stats["tail_abort"])+
          " actual_original_Bloodborne_functions=0")

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,UnicodeError) as exc:
        print("NATIVE_V402_NATIVE_FALLBACK_OVERLAY_REFUSED: "+
              type(exc).__name__+": "+str(exc)[:160],file=sys.stderr)
        raise SystemExit(2)
