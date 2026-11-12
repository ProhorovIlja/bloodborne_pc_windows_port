#!/usr/bin/env python3
"""V396 fail-closed, local-only generated import-callsite coverage gate.

Invented public fixture OR owner-private manifest. This parses every
bbrecomp-generated C shard to enumerate rc->call from actual native
RcFunction bodies, compares exact site/return contracts against an
INDEPENDENTLY declared allowlist, and checks SHA256 of the build-time
input image without disclosing any source bytes or private addresses.
Owner-private use MUST stay on private storage/CI, never public GitHub.

This proves *synthetic fixture source callsite coverage only*. Real game
indirect CALL target sets, guest imports, ABI and link/boot completeness
are NOT established by this source-text audit.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
PINNED="8f31ec7c41f252730c6325d52647046baef7549f"
FUNC_RE=re.compile(r"\bvoid\s+f_([0-9a-f]+)\s*\(\s*BbCpu\s*\*\s*c\s*\)\s*\{")
DECL_RE=re.compile(r"\bvoid\s+f_([0-9a-f]+)\s*\(\s*BbCpu\s*\*\s*c\s*\)\s*;")
CALL_RE=re.compile(r"\brc\s*->\s*call\s*\(\s*c\s*,[^;]*?\bB\s*\+\s*0x([0-9a-f]+)ull\s*\)",re.DOTALL)
CALL_ANY=re.compile(r"\brc\s*->\s*call\s*\(")
STEP_RE=re.compile(r"\brc\s*->\s*step\s*\(")
SHARD_RE=re.compile(r"recomp_\d{5}\.c\Z")
MAX_IMAGE=16*1024*1024*1024
MAX_MANIFEST=2_000_000
MAX_SHARDS=128
MAX_CODE=20_000_000
MAX_FUNCTIONS=100000
MAX_CALLS=8192
U64_MAX=(1<<64)-1

def number(value:object)->int:
    if not isinstance(value,str) or not re.fullmatch(r"0x(?:0|[1-9a-f][0-9a-f]*)",value):
        raise ValueError("noncanonical lowercase uint64 hex value")
    result=int(value,16)
    if result>U64_MAX:
        raise ValueError("address overflow")
    return result

def digest(file:Path)->str:
    h=hashlib.sha256()
    total=0
    with file.open("rb") as input_file:
        while True:
            chunk=input_file.read(1<<20)
            if not chunk:break
            total+=len(chunk)
            if total>MAX_IMAGE:raise ValueError("image exceeds private local bound")
            h.update(chunk)
    if not total:raise ValueError("empty image")
    return h.hexdigest()

def load_manifest(path:Path,scope:str)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_MANIFEST:
        raise ValueError("missing/symlinked/oversized manifest")
    m=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(m,dict) or set(m)!={"schema_version","scope","upstream_revision",
        "image_sha256","image_base","function_offsets","calls"}:
        raise ValueError("manifest schema/fields mismatch")
    if m["schema_version"]!=1 or m["scope"]!=scope or m["upstream_revision"]!=PINNED:
        raise ValueError("scope or compiler pin mismatch")
    if not isinstance(m["image_sha256"],str) or not re.fullmatch(r"[0-9a-f]{64}",m["image_sha256"]) or m["image_sha256"]=="0"*64:
        raise ValueError("missing image provenance fingerprint")
    number(m["image_base"])
    ff=m["function_offsets"]
    if not isinstance(ff,list) or not 1<=len(ff)<=MAX_FUNCTIONS:
        raise ValueError("function count invalid")
    funcs=[number(x) for x in ff]
    if funcs!=sorted(set(funcs)):
        raise ValueError("duplicate/unsorted owner AOT function")
    cc=m["calls"]
    if not isinstance(cc,list) or not 1<=len(cc)<=MAX_CALLS:
        raise ValueError("import callsite count invalid")
    for x in cc:
        if not isinstance(x,dict) or set(x)!={"function_offset","next_offset",
            "guest_target","service","recover_code","constant"}:
            raise ValueError("callsite schema mismatch")
        for attr in ("function_offset","next_offset","guest_target","constant"):
            number(x[attr])
        if number(x["guest_target"])==0:
            raise ValueError("null guest native import target")
        if x["service"] not in {"return_constant","add_qwords","cooperative_failure"} or (
            not isinstance(x["recover_code"],int) or isinstance(x["recover_code"],bool) or
            not 0<=x["recover_code"]<=32767):
            raise ValueError("unapproved native service")
        if x["service"]=="cooperative_failure":
            if x["recover_code"]<=503 or number(x["constant"])!=0:
                raise ValueError("invalid cooperative failure")
        elif x["recover_code"]!=0 or (x["service"]=="add_qwords" and number(x["constant"])!=0):
            raise ValueError("invalid service configuration")
    return m

def scan_generated(table:str,shards:list[str],image_base:int):
    declarations=DECL_RE.findall(table)
    if not declarations or len(declarations)!=len(set(declarations)):
        raise ValueError("duplicate/missing real RcFunction declarations")
    if table.count("const RcFunction *bb_recomp_init(")!=1:
        raise ValueError("missing real generated function registry")
    for d in declarations:
        if table.count("&d_"+d)!=1:
            raise ValueError("missing/duplicate real direct native function slot")
    bodies=[]
    observed=[]
    all_calls=0
    for text in shards:
        if STEP_RE.search(text):
            raise ValueError("guest interpreter STEP pathway is forbidden")
        found=list(FUNC_RE.finditer(text))
        if not found:raise ValueError("no genuine AOT body in shard")
        for i,m in enumerate(found):
            name=m.group(1)
            start=m.end()
            stop=found[i+1].start() if i+1<len(found) else len(text)
            body=text[start:stop]
            calls=CALL_RE.findall(body)
            cnt=len(CALL_ANY.findall(body))
            all_calls+=cnt
            if len(calls)!=cnt:raise ValueError("unparsed generated RcApi.call site")
            for nxt in calls:
                next_offset=int(nxt,16)
                off=int(name,16)
                if next_offset<=off or next_offset>U64_MAX-image_base:
                    raise ValueError("invalid generated return-site")
                observed.append((off,next_offset))
            bodies.append(name)
    if sorted(bodies)!=sorted(declarations) or len(bodies)!=len(declarations):
        raise ValueError("incomplete compiled source body inventory")
    if all_calls!=len(observed):
        raise ValueError("incomplete callsite scanner")
    return [int(x,16) for x in declarations],observed

def verify(manifest:dict,image_hash:str,table:str,shards:list[str])->dict:
    if image_hash!=manifest["image_sha256"]:
        raise ValueError("owner image fingerprint differs from declared provenance")
    base=number(manifest["image_base"])
    functions,actual=scan_generated(table,shards,base)
    expected=[number(x) for x in manifest["function_offsets"]]
    if sorted(functions)!=expected:
        raise ValueError("function manifest does not cover actual generated AOT table")
    sites=[]
    targets=set()
    seen_sites=set()
    for c in manifest["calls"]:
        off=number(c["function_offset"])
        nxt=number(c["next_offset"])
        target=number(c["guest_target"])
        if target==0 or target==base+nxt or base+nxt>U64_MAX:
            raise ValueError("invalid import/continuation target")
        if off not in expected or (off,nxt) in seen_sites or target in targets:
            # V395 imported target uniqueness remains an explicit ABI limit.
            raise ValueError("duplicate/unowned import callsite/target")
        seen_sites.add((off,nxt));targets.add(target);sites.append((off,nxt))
    if sorted(sites)!=sorted(actual):
        raise ValueError("missing/extra imported native callsite in closure manifest")
    if len(actual)!=len(manifest["calls"]):
        raise ValueError("partial generated import coverage")
    return {"functions":len(functions),"import_calls":len(actual),
        "exact_source_sites_covered":True,"image_fingerprint_verified":True,
        "original_game_boot_proven":False}

def render_header(m:dict)->str:
    base=number(m["image_base"])
    names={"return_constant":"SHYT_V395_RETURN_VALUE",
           "add_qwords":"SHYT_V395_ADD_GUEST_QWORDS",
           "cooperative_failure":"SHYT_V395_COOPERATIVE_FAILURE"}
    rows=[]
    for c in m["calls"]:
        off=number(c["function_offset"])
        nxt=number(c["next_offset"])
        target=number(c["guest_target"])
        value=number(c["constant"])
        rows.append("  {UINT64_C(0x%x), {UINT64_C(0x%x), UINT64_C(0x%x), %s, %d, UINT64_C(0x%x)}},"%
            (off,target,base+nxt,names[c["service"]],c["recover_code"],value))
    return ("/* GENERATED BY V396 LOCAL ORIGINAL-FREE MANIFEST ATTESTOR.\n"
            " * NOT a Bloodborne game import manifest or executable.\n"
            " */\n#ifndef SHYT_V396_IMPORT_CLOSURE_HEADER\n"
            "#define SHYT_V396_IMPORT_CLOSURE_HEADER\n"
            "#include <stdint.h>\n"
            "#include \"native_verified_import_v395.h\"\n"
            "typedef struct ShytV396Site {uint64_t caller_offset; "
            "ShytNativeImportSpecV395 import;} ShytV396Site;\n"
            "static const ShytV396Site shyt_v396_sites[] = {\n"+
            "\n".join(rows)+"\n};\n"
            "enum { SHYT_V396_SITE_COUNT = sizeof(shyt_v396_sites)/"
            "sizeof(shyt_v396_sites[0]) };\n"
            "#endif\n")

def run()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--scope",choices=["invented-test-only","owner-private"],required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--image",type=Path,required=True)
    p.add_argument("--table",type=Path,required=True)
    p.add_argument("--out-header",type=Path,required=True)
    a=p.parse_args()
    import importlib.util
    spec=importlib.util.spec_from_file_location(
        "v390_attestor",ROOT/"instrument_generated_aot_memory_v390.py")
    if not spec or not spec.loader:raise ValueError("pinned source lock unavailable")
    v390=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v390)
    v390.verify_generator(a.upstream_checkout)
    m=load_manifest(a.manifest,a.scope)
    image=a.image.resolve(strict=True)
    table=a.table.resolve(strict=True)
    out=a.out_header.absolute()
    if any(x.is_symlink() for x in (a.image,a.table)) or not image.is_file() or (
        not table.is_file()) or table.name!="recomp.c" or (
        table.stat().st_size>MAX_CODE) or out.exists() or (
        out.suffix!=".h") or not out.parent.is_dir() or out.parent.is_symlink():
        raise ValueError("invalid temporary generated path")
    if a.scope=="owner-private" and (
        any((x/".git").exists() for x in (out.parent,*out.parent.parents))):
        raise ValueError("owner-only generated header cannot be published into a repo")
    folder=table.parent
    raw=sorted(p for p in folder.iterdir() if SHARD_RE.fullmatch(p.name))
    if not raw or len(raw)>MAX_SHARDS or [p.name for p in raw]!=[
        f"recomp_{i:05d}.c" for i in range(len(raw))]:
        raise ValueError("missing/extra source shard")
    patched=sorted(folder.glob("recomp_*_v390.c"))
    if len(raw)!=len(patched):raise ValueError("not all source shards instrumented")
    shards=[]
    for f in raw:
        companion=f.with_name(f.stem+"_v390.c")
        if (f.is_symlink() or not companion.is_file() or
            companion.is_symlink() or f.stat().st_size>MAX_CODE or
            companion.stat().st_size>MAX_CODE+1000):
            raise ValueError("missing oversized source shard")
        s=f.read_text(encoding="utf-8")
        valid,_=v390.transform(s)
        if valid!=companion.read_text(encoding="utf-8"):
            raise ValueError("untrusted generated memory instrumentation")
        shards.append(s)
    status=verify(m,digest(image),table.read_text(encoding="utf-8"),shards)
    out.write_text(render_header(m),encoding="utf-8")
    print("NATIVE_V396_SOURCE_PINNED_IMPORT_CLOSURE_MANIFEST_PASS")
    # Only bounded counts + booleans. Never leak private owner source,
    # addresses, filenames, SHA-256 or commercial original content.
    print(json.dumps(status,sort_keys=True))

if __name__=="__main__":
    try:run()
    except (OSError,ValueError,UnicodeError,RuntimeError) as e:
        print("NATIVE_V396_IMPORT_CLOSURE_REFUSED: "+type(e).__name__+
              ": "+str(e)[:140],file=sys.stderr)
        raise SystemExit(2)
