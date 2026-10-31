#!/usr/bin/env python3
"""V199: real bbrecomp *whole-function* path over a wholly invented ELF64.

Proves full scanner/function-size/RET/direct CALL generator output without
original PS4 code or EBOOT. Source-only synthetic fixture. All game-derived
C and original user executables remain PRIVATE, never passed to GitHub CI.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import sys

UPSTREAM="8f31ec7c41f252730c6325d52647046baef7549f"
SOURCE_BLOB="f5032c9ead4988579e005af8a0a0ce4ba4ab66d8"
# Completely invented x86-64 functions from the user's desired PC architecture.
# Native tests exercise ordinary heap memory, unaligned memory, lazy x86
# flags with intra-function branches, and PC-relative virtual addresses.
FUNCTIONS=(
    (0x1000,bytes.fromhex("488b07c3"),"read_u64"),
    (0x1010,bytes.fromhex("488937c3"),"write_u64"),
    (0x1020,bytes.fromhex("4885ff74044889f8c331c0c3"),"test_jz_both_paths"),
    (0x1030,bytes.fromhex("488b074801f0c3"),"read_add"),
    (0x1050,bytes.fromhex("488d0539000000c3"),"rip_relative_lea"),
    (0x1070,bytes.fromhex("488b4701c3"),"unaligned_read"),
)
OFFSET_NAMES=tuple(f"f_{offset:x}" for offset,_,_ in FUNCTIONS)
MAX_TOTAL_BYTES=2_000_000

def gitblob(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def invented_elf()->bytes:
    elf=bytearray(0x1100)
    ident=b"\x7fELF\x02\x01\x01"+b"\0"*9
    header=struct.pack("<16sHHIQQQIHHHHHH",ident,2,62,1,0x1000,
                       0x40,0,0,64,56,1,0,0,0)
    elf[:64]=header
    elf[0x40:0x40+56]=struct.pack("<IIQQQQQQ",
                                 1,5,0x1000,0x1000,0,
                                 0x100,0x100,0x1000)
    for offset,body,_ in FUNCTIONS:
        assert 0x1000<=offset<0x1100 and offset+len(body)<=0x1100
        elf[offset:offset+len(body)]=body
    return bytes(elf)

def audit_generated(table:str,body:str)->dict:
    if table.count("const RcFunction *bb_recomp_init(")!=1:
        raise ValueError("original upstream dispatch table entry is absent")
    for (offset,machine,label),name in zip(FUNCTIONS,OFFSET_NAMES):
        if table.count("void "+name+"(BbCpu *c);")!=1:
            raise ValueError("original generated function declaration missing: "+label)
        if body.count("void "+name+"(BbCpu *c) {")!=1:
            raise ValueError("original generated function body missing: "+label)
        if f"&d_{offset:x}" not in table:
            raise ValueError("original dispatch slot missing: "+label)
    if "rc_ld(" not in body or "rc_st(" not in body:
        raise ValueError("missing true guest memory load/store paths")
    if "rc_cond(" not in body:
        raise ValueError("missing original lazy x86 flags conditional branch")
    if "B + 0x1090ull" not in body and "B + 0x1090" not in body:
        raise ValueError("missing relocated RIP-relative immediate address")
    if sum(len(x) for x in (table,body))>MAX_TOTAL_BYTES:
        raise ValueError("unexpectedly large synthetic original C")
    return {"original_bbrecomp_whole_functions":len(FUNCTIONS),
            "memory_read_write":True, "x86_lazy_flags_conditional_jz":True,
            "rip_relative":True, "unaligned_read":True,
            "real_game_data":False,"native_game_boot_proven":False}

def generate(checkout:Path,out:Path)->dict:
    checkout=checkout.resolve(strict=True)
    rev=subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],
                                text=True,stderr=subprocess.DEVNULL).strip()
    if rev!=UPSTREAM:raise ValueError("original source revision mismatch")
    src=subprocess.check_output(["git","-C",str(checkout),"show",
                                 "HEAD:tools/recomp/bbrecomp.c"])
    if gitblob(src)!=SOURCE_BLOB:
        raise ValueError("original full recompiler source SHA mismatch")
    compiler=checkout/"out/recomp/bbrecomp"
    if not compiler.is_file():raise ValueError("full original recompiler not built")
    if out.exists() or not out.parent.is_dir() or out.parent.is_symlink():
        raise ValueError("requires a fresh off-git generated C target")
    if any((p/".git").exists() for p in (out.parent,*out.parent.parents)):
        raise ValueError("game-shaped generated C must stay outside any git checkout")
    elf=out.parent/"INVENTED_NATIVE_MEMORY_BRANCHES_NOT_BLOODBORNE.elf"
    tsv=out.parent/"functions.tsv"
    offsets=out.parent/"function_offsets.txt"
    if any(p.exists() for p in (elf,tsv,offsets)):
        raise ValueError("synthetic input scratch collision")
    elf.write_bytes(invented_elf())
    tsv.write_text("start\tsize\tinsns\tundecodable\n"+
                   "".join(f"0x{address:016x}\t{len(body)}\t2\t0\n"
                           for address,body,_ in FUNCTIONS),encoding="ascii")
    offsets.write_text("".join(f"0x{address:x}\n"
                               for address,_,_ in FUNCTIONS),encoding="ascii")
    cmd=[str(compiler),str(elf),str(tsv),str(out),"@"+str(offsets)]
    run=subprocess.run(cmd,cwd=checkout,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       timeout=120)
    if run.returncode:
        raise RuntimeError("original full-function codegen failed on synthetic branches/memory ELF: "+
                           (run.stderr or run.stdout)[-700:].decode(errors="replace"))
    extra=out.with_name(out.stem+"_00000.c")
    if not out.is_file() or not extra.is_file():
        raise ValueError("full generator did not emit separate RcFunction and function C files")
    result=audit_generated(out.read_text(encoding="utf-8"),
                           extra.read_text(encoding="utf-8"))
    print("SHYT_NATIVE_V199_ORIGINAL_FULL_FUNCTION_GENERATOR_SYNTHETIC_ELF_PASS")
    print(result)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    try:generate(a.upstream_checkout,a.out)
    except (ValueError,RuntimeError,OSError,subprocess.CalledProcessError) as e:
        print(type(e).__name__+": "+str(e)[:350],file=sys.stderr)
        raise SystemExit(2)
