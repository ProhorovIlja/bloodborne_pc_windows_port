#!/usr/bin/env python3
"""Native V392: whole-shard fail-closed inventory of real pinned generated AOT C.

Checks that EVERY original generated recomp_NNNNN.c shard is represented
by an instrumented recomp_NNNNN_v390.c file with EXACTLY the known V390
overlay insertion, rather than silently compiling even one unmediated
guest-memory shard. Does not inspect/decrypt/distribute retail game code.
A source-text check is NOT a full C AST or binary proof.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v390_gated_memory",
    ROOT/"instrument_generated_aot_memory_v390.py")
if spec is None or spec.loader is None:
    raise RuntimeError("pinned V390 source instrumenter unavailable")
v390=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v390)
MAX_SHARDS=128
SHARD_RE=re.compile(r"recomp_(\d{5})\.c\Z")
DECL_RE=re.compile(r"\bvoid\s+(f_[0-9a-f]+)\s*\(\s*BbCpu\s*\*\s*c\s*\)\s*;")
BODY_RE=re.compile(r"\bvoid\s+(f_[0-9a-f]+)\s*\(\s*BbCpu\s*\*\s*c\s*\)\s*\{")
RAW_POINTER_RE=re.compile(
    r"\b(?:bb_load|bb_store|bb_fence_load|bb_fence_store)\s*\("
    r"|\bmemcpy\s*\(\s*\(\s*(?:const\s+)?void\s*\*\s*\)"
)

def audit(table:str,shards:list[tuple[str,str]],
          functions:int,require_lock_simd:bool=True)->dict[str,object]:
    if not 1<=functions<=100000 or not 1<=len(shards)<=MAX_SHARDS:
        raise ValueError("invalid function/shard count")
    if table.count("const RcFunction *bb_recomp_init(")!=1:
        raise ValueError("missing exact pinned generated function table")
    declarations=DECL_RE.findall(table)
    if len(declarations)!=functions or len(set(declarations))!=functions:
        raise ValueError("function table coverage is incomplete or duplicated")
    for symbol in declarations:
        off=symbol[2:]
        if table.count("&d_"+off)!=1:
            raise ValueError("direct native AOT slot missing or duplicated")
    found:list[str]=[]
    helpers={k:0 for k in v390.CALLS}
    for original,instrumented in shards:
        if len(original.encode("utf-8"))>v390.MAX_SOURCE:
            raise ValueError("original generated shard exceeds size bound")
        expected,counts=v390.transform(original)
        if expected!=instrumented:
            raise ValueError("not an exact original generated C plus V390 overlay")
        if RAW_POINTER_RE.search(original):
            raise ValueError("unmediated memory access in generated function")
        if re.search(r"\brc\s*->\s*step\s*\(",original):
            raise ValueError("interpreter STEP callback in generated function")
        bodies=BODY_RE.findall(original)
        if not bodies or len(bodies)!=len(set(bodies)):
            raise ValueError("generated shard has absent/duplicate functions")
        found.extend(bodies)
        for key in helpers: helpers[key]+=counts[key]
    if len(found)!=functions or sorted(found)!=sorted(declarations):
        raise ValueError("not every generated function has exactly one instrumented body")
    if require_lock_simd and (
        helpers["rc_cas"]<1 or helpers["rc_vld"]<2 or helpers["rc_vst"]<2):
        raise ValueError("source-locked generated LOCK and 128/256 SIMD not covered")
    return {"generated_functions":functions,"instrumented_shards":len(shards),
            "actual_memory_helper_calls":helpers,
            "game_boot_proven":False,"retail_game_bytes":False}


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream-checkout",required=True,type=Path)
    parser.add_argument("--table",required=True,type=Path)
    parser.add_argument("--expected-functions",type=int,required=True)
    args=parser.parse_args()
    v390.verify_generator(args.upstream_checkout)
    table=args.table.resolve(strict=True)
    if table.name!="recomp.c" or table.is_symlink() or not table.is_file():
        raise ValueError("only runner temporary pinned recomplier output is supported")
    folder=table.parent
    if any((p/".git").exists() for p in (folder,*folder.parents)):
        raise ValueError("generated C cannot be inside source repositories")
    raw_shards=sorted(p for p in folder.iterdir()
                      if SHARD_RE.fullmatch(p.name))
    if not raw_shards or len(raw_shards)>MAX_SHARDS or (
       [p.name for p in raw_shards]!=[
           f"recomp_{i:05d}.c" for i in range(len(raw_shards))]):
        raise ValueError("incomplete or noncontiguous source shard sequence")
    patched=sorted(p for p in folder.iterdir()
        if re.fullmatch(r"recomp_\d{5}_v390\.c",p.name))
    if len(patched)!=len(raw_shards):
        raise ValueError("unpatched or unexpected generated shard")
    pairs=[]
    for source in raw_shards:
        companion=source.with_name(source.stem+"_v390.c")
        if (source.is_symlink() or not companion.is_file() or
            companion.is_symlink() or
            source.stat().st_size>v390.MAX_SOURCE or
            companion.stat().st_size>v390.MAX_SOURCE+1000):
            raise ValueError("missing/unsafe/oversized generated C")
        pairs.append((source.read_text(encoding="utf-8"),
                      companion.read_text(encoding="utf-8")))
    result=audit(table.read_text(encoding="utf-8"),
                 pairs,args.expected_functions)
    print("NATIVE_V392_ALL_REAL_GENERATED_AOT_SHARDS_INSTRUMENTED_PASS")
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,UnicodeError,RuntimeError) as e:
        print("NATIVE_V392_GENERATED_INVENTORY_REFUSED: "+
              type(e).__name__,file=sys.stderr)
        raise SystemExit(2)
