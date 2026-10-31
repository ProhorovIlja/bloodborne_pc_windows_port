#!/usr/bin/env python3
"""V194: verify ALL native x64 BbCpu fields against exact public upstream C.

Never needs private eboot, game dump, generated game C, platform emulation or
private object code. Exact SHA pins make upstream ABI drift a hard failure.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import re
import subprocess

UPSTREAM="8f31ec7c41f252730c6325d52647046baef7549f"
UPSTREAM_BLOBS={
    "src/cpu/cpu_internal.h":"bcbd422f92a84087a2e0c2d260ec64040f381540",
    "src/recomp/rc.h":"a27b8f5fc872c75bd08f6788d716b6856c9e2309",
}
HERE=Path(__file__).resolve().parent
OWN="full_cpu_abi_v194.h"

def sha_blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()

def cpu_fields(source:str,upstream:bool)->list[str]:
    pattern=(r"typedef\s+struct\s+BbCpu\s*\{(.*?)\}\s*BbCpu\s*;"
             if upstream else r"struct\s+BbCpu\s*\{(.*?)\}\s*;")
    found=re.search(pattern,source,re.S)
    if not found:raise ValueError("BbCpu full definition missing")
    body=re.sub(r"/\*.*?\*/","",found.group(1),flags=re.S)
    body=re.sub(r"//[^\n]*","",body)
    fields=[]
    for part in body.split(";"):
        part=re.sub(r"\s+"," ",part).strip()
        if not part:continue
        part=part.replace("struct BbWatch *","BbWatch *")
        fields.append(part)
    return fields

def run(root:Path,own:Path)->dict:
    root=root.resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                               text=True,stderr=subprocess.DEVNULL).strip()!=UPSTREAM:
        raise ValueError("public upstream pin changed")
    original={}
    for name,pin in UPSTREAM_BLOBS.items():
        raw=subprocess.check_output(["git","-C",str(root),"show","HEAD:"+name])
        if sha_blob(raw)!=pin:raise ValueError("upstream blob changed: "+name)
        original[name]=raw.decode("utf-8")
    actual=cpu_fields(original["src/cpu/cpu_internal.h"],True)
    expected=cpu_fields(own.read_text(encoding="utf-8"),False)
    if expected!=actual:
        raise ValueError("complete BbCpu field type/order drift")
    rc=original["src/recomp/rc.h"]
    gates=(
        "#define BB_RECOMP_API_VERSION 4u",
        "typedef struct { uint64_t offset, size, hash; RcFn fn; RcFn *direct; } RcFunction;",
        "typedef const RcFunction *(*RcInit)(const RcApi *api, size_t *count);",
        "uint64_t (*step)(BbCpu *cpu);",
        "void (*call)(BbCpu *cpu, uint64_t target, uint64_t next);",
        "void (*tail)(BbCpu *cpu);",
        "void (*bail)(BbCpu *cpu, uint64_t entry_rsp);",
        "void (*trace)(uint64_t offset, const uint64_t r[16], const BbCpu *cpu);",
    )
    for gate in gates:
        if rc.count(gate)!=1:raise ValueError("upstream v4 callback contract changed")
    return {"status":"PASS","full_cpu_field_declarations":len(actual),
            "native_abi_verified":True,"win64_executable_game_proven":False,
            "original_eboot_used":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--upstream-checkout",required=True,type=Path)
    ap.add_argument("--our-header",type=Path,default=HERE/OWN)
    args=ap.parse_args()
    print(run(args.upstream_checkout,args.our_header))
