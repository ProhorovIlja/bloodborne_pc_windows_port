#!/usr/bin/env python3
"""V200: real bbrecomp *whole-function* path over a wholly invented ELF64.

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
# Entirely SYNTHETIC x86-64 bytecode: original full bbrecomp normal mode.
# CALL RAX, CALL QWORD PTR [RDI], and a register-moved indirect CALL all
# target other compiled native functions using the generated RcFunction table.
FUNCTIONS=(
    (0x1000,bytes.fromhex("ffd0c3"),"register_indirect_call"),
    (0x1010,bytes.fromhex("ff17c3"),"pointer_slot_indirect_call"),
    (0x1020,bytes.fromhex("48c7c02a000000c3"),"native_return_42"),
    (0x1030,bytes.fromhex("4889f8ffd0c3"),"move_and_indirect_call"),
    (0x1050,bytes.fromhex("48c7c063000000c3"),"native_return_99"),
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
        raise ValueError("original public whole-generator export missing")
    for (offset,_,label),name in zip(FUNCTIONS,OFFSET_NAMES):
        if table.count("void "+name+"(BbCpu *c);")!=1:
            raise ValueError("original native function table missing "+label)
        if body.count("void "+name+"(BbCpu *c) {")!=1:
            raise ValueError("original native function body missing "+label)
        if f"&d_{offset:x}" not in table:
            raise ValueError("original direct entrypoint missing "+label)
    if table.count("RcFn rc_native_find(uint64_t target)")!=1:
        raise ValueError("no new native AOT binary-search function")
    if "while (lo < hi)" not in table or "table[mid].offset" not in table:
        raise ValueError("missing indexed native AOT offset search")
    if "rc_native_find(t)" not in body:
        raise ValueError("original indirect CALL still only uses runtime handler")
    if body.count("rc_native_find(t)")<3:
        raise ValueError("not all indirect register/memory CALL sites handled")
    if "rc->call(c, t" not in body:
        raise ValueError("unknown/import fallback attribution missing")
    if sum(len(x) for x in (table,body))>MAX_TOTAL_BYTES:
        raise ValueError("unexpected synthetic generated C size")
    return {"real_bbrecomp_whole_functions":len(FUNCTIONS),
            "original_native_index_binary_search":True,
            "indirect_register_call":True,
            "indirect_pointer_slot_call":True,
            "runtime_eboot_required":False,
            "actual_bloodborne_boot_proven":False}

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
    elf=out.parent/"INVENTED_INDIRECT_CALLS_NOT_BLOODBORNE.elf"
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
        raise RuntimeError("original full-game C generation failed on invented ELF: "+
                           (run.stderr or run.stdout)[-700:].decode(errors="replace"))
    extra=out.with_name(out.stem+"_00000.c")
    if not out.is_file() or not extra.is_file():
        raise ValueError("full generator did not emit separate RcFunction and function C files")
    result=audit_generated(out.read_text(encoding="utf-8"),
                           extra.read_text(encoding="utf-8"))
    print("SHYT_NATIVE_V200_ORIGINAL_FULL_FUNCTION_GENERATOR_SYNTHETIC_ELF_PASS")
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
