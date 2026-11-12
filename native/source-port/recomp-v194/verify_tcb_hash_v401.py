#!/usr/bin/env python3
"""V401 independent *bounded synthetic* decoder-aware function hash test.

A real pinned bbcpu decoder treats MOV reg64,fs:[0] and
MOV reg64,gs:[disp32] as special TCB loads, normalized to
FNV-1a64(MIX 0xf5,MIX destination_reg), not original bytes. The
positive and negative control is MOV rax,fs:[0x40] which MUST hash
raw encoded x86 bytes. These exact invented x86/RET sequences are
predeclared; no universal x86 decoder or real Bloodborne hashes.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
PINNED="8f31ec7c41f252730c6325d52647046baef7549f"
HASH_BLOB="2e005442aacaa835e5b3c2f3522d63b0c04bc8fd"
DECODE_BLOB="e3a84f800ae70f78ccaea6ea7c456ebd97d502fc"
IMAGE_SHA256="2760a66cf59de42bec003c189ca64f6c9a67bb1e38492626fdcd5bcb5789a94f"
BASE=0x400000
MASK=(1<<64)-1
MODES=("raw","tcb_rax_fs0","tcb_rax_gs40","tcb_rbx_fs0",
       "raw_fs_nonzero","tcb_rbx_gs40")
FS_MOV_RAX0="64488b042500000000c3"
GS_MOV_RAX40="65488b042540000000c3"
FS_MOV_RBX0="64488b1c2500000000c3"
FS_MOV_RAX40="64488b042540000000c3"
GS_MOV_RBX40="65488b1c2540000000c3"
EXPECTED=(
("0x1000","f0480fb137c3","raw","0xcaf2b035bd6212e7"),
("0x1020","f30f6f07c3","raw","0x52a0aa93ab618e9a"),
("0x1040","f30f7f07c3","raw","0xc807fa935cdff0ea"),
("0x1060","c5fe6f07c3","raw","0xd3a4d7bcf8b8f381"),
("0x1080","c5fe7f07c3","raw","0x490c27bcaa3755d1"),
("0x10a0","ffd0c3","raw","0xfa30281be4fbf37b"),
("0x10c0","ffd0c3","raw","0xfa30281be4fbf37b"),
("0x10e0",FS_MOV_RAX0,"tcb_rax_fs0","0xa2827e1bb306bdc9"),
("0x1100",GS_MOV_RAX40,"tcb_rax_gs40","0xa2827e1bb306bdc9"),
("0x1120",FS_MOV_RBX0,"tcb_rbx_fs0","0xa28cae1bb30f63de"),
("0x1140",FS_MOV_RAX40,"raw_fs_nonzero","0x844cf2c7d6d2b746"),
("0x1160",GS_MOV_RBX40,"tcb_rbx_gs40","0xa28cae1bb30f63de"),
)

def fnv(data:bytes)->int:
    h=0xcbf29ce484222325
    for byte in data:h=((h^byte)*0x100000001b3)&MASK
    return h

def canonical_hash(code:bytes,mode:str)->int:
    if mode in ("tcb_rax_fs0","tcb_rax_gs40",
                "tcb_rbx_fs0","tcb_rbx_gs40"):
        if len(code)!=10 or code[-1]!=0xc3 or (
            code[1:3]!=bytes.fromhex("488b") or code[4]!=0x25) or (
            code[3] not in (0x04,0x1c)):
            raise ValueError("not the source-locked special TCB MOV encoding")
        reg={0x04:0,0x1c:3}[code[3]]
        segment=code[0]
        disp=int.from_bytes(code[5:9],"little",signed=True)
        if not ((segment==0x64 and disp==0) or segment==0x65):
            raise ValueError("not an authentic pinned FS-zero/GS-absolute TCB load")
        if ("rax" in mode)!=(reg==0) or ("rbx" in mode)!=(reg==3):
            raise ValueError("claimed decoded register differs")
        return fnv(bytes([0xf5,reg,0xc3]))
    if mode=="raw_fs_nonzero":
        if code.hex()!=FS_MOV_RAX40:
            raise ValueError("FS nonzero displacement must NOT use TCB special")
    elif mode!="raw":
        raise ValueError("unknown decoded hashing mode")
    return fnv(code)

def load_manifest(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>30000:
        raise ValueError("missing bounded TCB hash manifest")
    m=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(m,dict) or set(m)!={
        "schema_version","scope","upstream_revision",
        "upstream_bbcpu_recomp_git_blob","upstream_bbcpu_decode_git_blob",
        "image_sha256","image_base","hash_algorithm","functions"} or (
        m["schema_version"]!=1 or m["scope"]!="invented-only" or
        m["upstream_revision"]!=PINNED or
        m["upstream_bbcpu_recomp_git_blob"]!=HASH_BLOB or
        m["upstream_bbcpu_decode_git_blob"]!=DECODE_BLOB or
        m["image_sha256"]!=IMAGE_SHA256 or m["image_base"]!="0x400000" or
        m["hash_algorithm"]!="pinned_bbcpu_decoded_fnv1a64_tcb_special"):
        raise ValueError("compiler/source identity provenance mismatch")
    rows=m["functions"]
    if not isinstance(rows,list) or len(rows)!=len(EXPECTED):
        raise ValueError("incomplete TCB-normalized identity manifest")
    for actual,expected in zip(rows,EXPECTED):
        off,code,mode,h=expected
        if not isinstance(actual,dict) or set(actual)!={
            "offset","code_hex","size","hash_mode","expected_hash"
        } or actual["offset"]!=off or actual["code_hex"]!=code or (
            actual["hash_mode"]!=mode) or actual["size"]!=len(code)//2 or (
            isinstance(actual["size"],bool)) or actual["expected_hash"]!=h or (
            canonical_hash(bytes.fromhex(code),mode)!=int(h,16)):
            raise ValueError("TCB hash, raw negative, opcode, size or offset drift")
    return m

def check_upstream(checkout:Path)->None:
    root=checkout.resolve(strict=True)
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                text=True).strip()
    if rev!=PINNED:raise ValueError("untrusted public bbrecomp revision")
    for file,expected in (("src/cpu/recomp.c",HASH_BLOB),
                          ("src/cpu/decode.c",DECODE_BLOB)):
        blob=subprocess.check_output(["git","-C",str(root),"rev-parse",
                                      "HEAD:"+file],text=True).strip()
        if blob!=expected:raise ValueError("pinned instruction decoder changed")
    # Inherited V400 validates all seven original-free function rows and
    # existing V390/396 source SHA/pinned generated C. This check ensures
    # we do NOT derive expected TCB bytes from compiler's own table.

def verify(m:dict,image:bytes,table:str,shard:str)->dict:
    if len(image)!=0x1200 or hashlib.sha256(image).hexdigest()!=IMAGE_SHA256:
        raise ValueError("invented FS GS image SHA256 mismatch")
    spec=importlib.util.spec_from_file_location(
        "v400_table",ROOT/"verify_native_function_identity_v400.py")
    if spec is None or spec.loader is None:
        raise ValueError("V400 table decoder not present")
    v400=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v400)
    tables=v400.TABLE.findall(table)
    if len(tables)!=1:raise ValueError("missing/extra actual RcFunction table")
    entries=re.findall(r"\{[^{}]*\}",tables[0])
    if len(entries)!=len(EXPECTED):
        raise ValueError("compiled table omits or adds TCB function")
    normalized=0
    for (off,hexcode,mode,h),row in zip(EXPECTED,entries):
        parsed=v400.ROWS.fullmatch(row)
        if not parsed:raise ValueError("unknown genuine compiled RcFunction row")
        actualoff,sz,actualhash,fn,direct=parsed.groups()
        target=int(off,16);code=bytes.fromhex(hexcode)
        if (int(actualoff,16)!=target or int(sz)!=len(code) or
            fn!=f"{target:x}" or direct!=fn or
            int(actualhash,16)!=int(h,16) or
            image[target:target+len(code)]!=code):
            raise ValueError("independent decoded TCB hash does not match pinned generator")
        matches=list(re.finditer(
            r"\bvoid\s+f_"+f"{target:x}"+r"\s*\(\s*BbCpu\s*\*c\s*\)\s*\{",
            shard))
        if len(matches)!=1:raise ValueError("actual generated function body missing")
        nextfn=re.search(r"\bvoid\s+f_[0-9a-f]+\s*\(\s*BbCpu\s*\*c\s*\)\s*\{",
                         shard[matches[0].end():])
        end=matches[0].end()+nextfn.start() if nextfn else len(shard)
        body=shard[matches[0].end():end]
        if mode.startswith("tcb_"):
            # Actual pinned bbrecomp must compile these to native
            # c->tcb loads rather than guest interpreter fallback.
            if not re.search(r"c->tcb\s*;",body) or "rc->step(" in body:
                raise ValueError("upstream did not emit direct native TCB load")
            normalized+=1
        if mode=="raw_fs_nonzero":
            if "c->tcb" in body or "rc->step(" not in body:
                raise ValueError("FS nonzero fallback must be visibly quarantined")
        elif "rc->step(" in body:
            raise ValueError("guest interpreter STEP found in native eligible probe")
    if normalized!=4:
        raise ValueError("TCB source/compiled hash normalization coverage incomplete")
    return {"compiled_functions":len(EXPECTED),"direct_tcb_functions":normalized,
            "fs_nonzero_interpreter_fallback_quarantined":True,
            "real_game_hashes_verified":False}

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--image",type=Path,required=True)
    p.add_argument("--table",type=Path,required=True)
    p.add_argument("--shard",type=Path,required=True)
    a=p.parse_args()
    check_upstream(a.upstream_checkout)
    manifest=load_manifest(a.manifest)
    for f in (a.image,a.table,a.shard):
        if f.is_symlink() or not f.is_file() or f.stat().st_size>2_000_000:
            raise ValueError("source-only generated file missing/oversized")
    result=verify(manifest,a.image.read_bytes(),
                  a.table.read_text(encoding="utf-8"),
                  a.shard.read_text(encoding="utf-8"))
    print("NATIVE_V401_PINNED_DECODED_FS_GS_TCB_HASH_IDENTITY_PASS")
    print("functions=12 normalized_tcb=4 FS_nonzero_negative=1")
    print("actual_original_game_hashes=FALSE original_game_boot=FALSE")

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,RuntimeError,UnicodeError,
            subprocess.CalledProcessError) as e:
        print("NATIVE_V401_TCB_IDENTITY_REFUSED: "+type(e).__name__+
              ": "+str(e)[:180],file=sys.stderr)
        raise SystemExit(2)
