#!/usr/bin/env python3
"""V402 fail-closed source-wide native AOT fallback closure for original-free x86.

Compare the REAL pinned bbrecomp 12-function probe (1 source-verified
translator STEP blocker) and a SEPARATELY compiled 11-function subset
that physically omits the fallback's code bytes and compiled function.
Only the latter may become a native host object or execute. Every
RcApi.call source site must match the independent V402 11-fn manifest.

This bounded source classifier is NOT a full x86 code/ABI/linker proof
for original Bloodborne 1.09. It does not execute guest interpreter.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
EXPECTED_SHA="d0a4371cc49793958cca2900f9b4e89c15031e8c71d9398d8cb5fe0e062676a5"
MAX_FILE=2_000_000
FUNC=re.compile(r"\bvoid\s+f_([0-9a-f]+)\s*\(\s*BbCpu\s*\*c\s*\)\s*\{")
API_CALL=re.compile(r"\brc\s*->\s*([a-zA-Z_]\w*)\s*\(")
DANGEROUS=re.compile(
    r"\b(?:bb_load|bb_store|bb_fence_load|bb_fence_store)\s*\("
    r"|\bmemcpy\s*\(\s*\(\s*(?:const\s+)?void\s*\*\s*\)")
KNOWN_CALLBACKS={"step","bail","call","tail","trace"}

def module(name:str,file:str):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    if not spec or not spec.loader:raise ValueError("pinned original-free verifier missing")
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def inventory(table:str,shard:str)->dict[int,dict]:
    """Every function body and every RcApi callback, no first-match skipping."""
    v400=module("v400_shape","verify_native_function_identity_v400.py")
    tables=v400.TABLE.findall(table)
    if len(tables)!=1 or table.count("const RcFunction *bb_recomp_init(")!=1:
        raise ValueError("missing/duplicated pinned real function registry")
    rows=re.findall(r"\{[^{}]*\}",tables[0])
    matches=list(FUNC.finditer(shard))
    if len(rows)!=len(matches) or not matches:
        raise ValueError("one-to-one table/function body closure broken")
    out={}
    for i,(row,m) in enumerate(zip(rows,matches)):
        parsed=v400.ROWS.fullmatch(row)
        if not parsed:raise ValueError("unexpected native function identity table schema")
        off,size,h,fn,direct=parsed.groups()
        offset=int(off,16)
        if offset!=int(m.group(1),16) or fn!=f"{offset:x}" or direct!=fn or (
            offset in out):
            raise ValueError("out of order/duplicated function/direct slot")
        end=matches[i+1].start() if i+1<len(matches) else len(shard)
        body=shard[m.end():end]
        if DANGEROUS.search(body):
            raise ValueError("source has uninstrumentable raw host guest pointer")
        seen=API_CALL.findall(body)
        if set(seen)-KNOWN_CALLBACKS:
            raise ValueError("unknown native RcApi callback requires ABI audit")
        out[offset]={"size":int(size),"hash":int(h,16),
                     "callbacks":tuple(seen),"body":body}
    return out

def evaluate(table12:str,shard12:str,image12:bytes,
             table11:str,shard11:str,image11:bytes,
             manifest:dict)->dict:
    v401=module("v401_hash","verify_tcb_hash_v401.py")
    v396=module("v396_site","audit_import_closure_v396.py")
    fixture=v401.load_manifest(ROOT/"native_tcb_hash_fixture_v401.json")
    status=v401.verify(fixture,image12,table12,shard12)
    if status["direct_tcb_functions"]!=4 or not status["fs_nonzero_interpreter_fallback_quarantined"]:
        raise ValueError("12-function decoded/TLS source parity changed")
    full=inventory(table12,shard12)
    safe=inventory(table11,shard11)
    if hashlib.sha256(image11).hexdigest()!=EXPECTED_SHA or len(image11)!=0x1200 or (
        image11[0x1140:0x114a]!=b"\0"*10):
        raise ValueError("native-only input ELF still contains forbidden FS nonzero bytes")
    expected={int(off,16):{"size":len(bytes.fromhex(code)),
            "hash":int(h,16)} for off,code,_,h in v401.EXPECTED}
    approval=set(expected)-{0x1140}
    if set(full)!=set(expected) or set(safe)!=approval or (
        len(full)!=12 or len(safe)!=11):
        raise ValueError("incomplete or falsely included compiled AOT function")
    permitted_calls={(0x10a0,"call"),(0x10c0,"call")}
    observed_calls=set()
    unsupported={}
    for offset,record in full.items():
        expected_row=expected[offset]
        if record["size"]!=expected_row["size"] or (
            record["hash"]!=expected_row["hash"]):
            raise ValueError("full source hash/size changed")
        unsafe=[c for c in record["callbacks"] if c in ("step","bail","tail","trace")]
        if unsafe:
            unsupported[offset]=tuple(unsafe)
    if unsupported!={0x1140:("step",)}:
        raise ValueError("unexpected/bypassed interpreter or translator fallback")
    for offset,record in safe.items():
        expected_row=expected[offset]
        if record["size"]!=expected_row["size"] or record["hash"]!=expected_row["hash"]:
            raise ValueError("native-only source hash/size changed")
        if any(x in ("step","bail","tail","trace") for x in record["callbacks"]):
            raise ValueError("interpreter/translator/tail/trace callback in promoted AOT")
        if record["callbacks"].count("call"):
            if offset not in (0x10a0,0x10c0) or (
                record["callbacks"].count("call")!=1):
                raise ValueError("unattested source-generated guest indirect CALL")
            observed_calls.add((offset,"call"))
        if offset not in full or record["body"]!=full[offset]["body"]:
            raise ValueError("native-only source differs from independently audited full source")
        code=next(bytes.fromhex(x[1]) for x in v401.EXPECTED if int(x[0],16)==offset)
        if image11[offset:offset+len(code)]!=code:
            raise ValueError("native-only source and image bytes conflict")
    if observed_calls!=permitted_calls:
        raise ValueError("not every native import callback is attested")
    if manifest["image_sha256"]!=EXPECTED_SHA or (
        [int(x,16) for x in manifest["function_offsets"]]!=sorted(approval)):
        raise ValueError("independent 11-function manifest changed")
    status=v396.verify(manifest,EXPECTED_SHA,table11,[shard11],
                       allow_shared_targets=True)
    if not status["exact_source_sites_covered"] or status["functions"]!=11 or (
        status["import_calls"]!=2):
        raise ValueError("runtime imported callsite closure unproven")
    return {"generated_source_functions":len(full),
            "quarantined_fallbacks":{"0x1140":["rc->step"]},
            "native_only_functions":len(safe),
            "native_indirect_call_sites":len(observed_calls),
            "runtime_original_game_proven":False}

def checked_file(path:Path,suffix:str)->bytes:
    if path.is_symlink() or not path.is_file() or path.suffix!=suffix or (
        path.stat().st_size>MAX_FILE):
        raise ValueError("missing, symlinked, oversized generated input")
    if any((p/".git").exists() for p in (path.parent,*path.parent.parents)):
        raise ValueError("generated input must stay OUTSIDE source repository")
    return path.read_bytes()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--full-table",required=True,type=Path)
    p.add_argument("--full-shard",required=True,type=Path)
    p.add_argument("--full-image",required=True,type=Path)
    p.add_argument("--native-table",required=True,type=Path)
    p.add_argument("--native-shard",required=True,type=Path)
    p.add_argument("--native-image",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--out-ledger",required=True,type=Path)
    p.add_argument("--upstream-checkout",required=True,type=Path)
    a=p.parse_args()
    v390=module("v390_generator","instrument_generated_aot_memory_v390.py")
    v390.verify_generator(a.upstream_checkout)
    v401=module("v401_hash","verify_tcb_hash_v401.py")
    v401.check_upstream(a.upstream_checkout)
    fulltable=checked_file(a.full_table,".c").decode("utf-8")
    fullshard=checked_file(a.full_shard,".c").decode("utf-8")
    fullimage=checked_file(a.full_image,".elf")
    nativetable=checked_file(a.native_table,".c").decode("utf-8")
    nativeshard=checked_file(a.native_shard,".c").decode("utf-8")
    nativeimage=checked_file(a.native_image,".elf")
    v396=module("v396_manifest","audit_import_closure_v396.py")
    manifest=v396.load_manifest(a.manifest,"invented-test-only")
    ledger=evaluate(fulltable,fullshard,fullimage,nativetable,
                    nativeshard,nativeimage,manifest)
    out=a.out_ledger
    if out.exists() or out.suffix!=".json" or not out.parent.is_dir() or (
        out.parent.is_symlink()) or (
        any((p/".git").exists() for p in (out.parent,*out.parent.parents))):
        raise ValueError("unsafe source ledger output path")
    out.write_text(json.dumps(ledger,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("NATIVE_V402_FULL_12_SOURCE_FALLBACK_LEDGER_AND_11_NATIVE_CLOSURE_PASS")
    print(json.dumps(ledger,sort_keys=True))
    print("no_original_Bloodborne_code_or_native_game_boot=TRUE")

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,UnicodeError,RuntimeError) as exc:
        print("NATIVE_V402_NATIVE_CLOSURE_REFUSED: "+
              type(exc).__name__+": "+str(exc)[:180],file=sys.stderr)
        raise SystemExit(2)
