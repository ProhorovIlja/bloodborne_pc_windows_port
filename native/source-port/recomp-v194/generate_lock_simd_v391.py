#!/usr/bin/env python3
"""Native V391: genuine pinned bbrecomp whole-functions for invented x86 LOCK/SIMD.

ELF64 is a disposable BUILD-TIME input only. All bytes are original
test instructions, never commercial game code and never loaded at runtime.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import sys

PINNED="8f31ec7c41f252730c6325d52647046baef7549f"
GENERATOR_BLOB="f5032c9ead4988579e005af8a0a0ce4ba4ab66d8"
FUNCTIONS=(
    (0x1000,bytes.fromhex("f0480fb137c3"),"lock_cmpxchg64_rdi_rsi"),
    (0x1020,bytes.fromhex("f30f6f07c3"),"movdqu_xmm_load"),
    (0x1040,bytes.fromhex("f30f7f07c3"),"movdqu_xmm_store"),
    (0x1060,bytes.fromhex("c5fe6f07c3"),"vmovdqu_ymm_load"),
    (0x1080,bytes.fromhex("c5fe7f07c3"),"vmovdqu_ymm_store"),
)
MAX_GENERATED=2_000_000

def blobhash(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def build_elf()->bytes:
    elf=bytearray(0x1200)
    ident=b"\x7fELF\x02\x01\x01"+b"\0"*9
    elf[:64]=struct.pack("<16sHHIQQQIHHHHHH",
        ident,2,62,1,0x1000,0x40,0,0,64,56,1,0,0,0)
    elf[0x40:0x40+56]=struct.pack("<IIQQQQQQ",
        1,5,0x1000,0x1000,0,0x200,0x200,0x1000)
    for offset,insn,_ in FUNCTIONS:
        assert offset>=0x1000 and offset+len(insn)<=0x1200
        elf[offset:offset+len(insn)]=insn
    return bytes(elf)

def make(checkout:Path,out:Path)->None:
    root=checkout.resolve(strict=True)
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
        text=True,stderr=subprocess.DEVNULL).strip()
    src=subprocess.check_output(["git","-C",str(root),"show",
        "HEAD:tools/recomp/bbrecomp.c"],stderr=subprocess.DEVNULL)
    if rev!=PINNED or blobhash(src)!=GENERATOR_BLOB:
        raise ValueError("pinned original full-generator SHA/revision mismatch")
    compiler=root/"out/recomp/bbrecomp"
    if not compiler.is_file() or out.exists() or not out.parent.is_dir() or (
         out.parent.is_symlink()):
        raise ValueError("build original generator first; output must be fresh")
    if any((d/".git").exists() for d in (out.parent,*out.parent.parents)):
        raise ValueError("generated code must stay OUTSIDE the repo")
    scratch=out.parent
    elf=scratch/"V391_INVENTED_LOCK_SIMD_NOT_BLOODBORNE.elf"
    tsv=scratch/"functions.tsv"
    offsets=scratch/"function_offsets.txt"
    if elf.exists() or tsv.exists() or offsets.exists():
        raise ValueError("refusing overwrite of synthetic generation inputs")
    elf.write_bytes(build_elf())
    tsv.write_text("start\tsize\tinsns\tundecodable\n"+
        "".join(f"0x{off:016x}\t{len(body)}\t2\t0\n"
            for off,body,_ in FUNCTIONS),encoding="ascii")
    offsets.write_text("".join(f"0x{off:x}\n"
       for off,_,_ in FUNCTIONS),encoding="ascii")
    run=subprocess.run([str(compiler),str(elf),str(tsv),str(out),
        "@"+str(offsets)],cwd=root,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,timeout=120)
    if run.returncode:
        raise RuntimeError("pinned real bbrecomp refused invented LOCK/SIMD: "+
            (run.stderr or run.stdout)[-600:].decode(errors="replace"))
    body=out.with_name(out.stem+"_00000.c")
    if not out.is_file() or not body.is_file():
        raise ValueError("missing actual upstream generated table/body C")
    table=out.read_text(encoding="utf-8")
    emitted=body.read_text(encoding="utf-8")
    if len(table)+len(emitted)>MAX_GENERATED:
        raise ValueError("generated source too large")
    for off,_,_ in FUNCTIONS:
        name=f"f_{off:x}"
        if table.count(f"void {name}(BbCpu *c);")!=1 or (
           emitted.count(f"void {name}(BbCpu *c) {{")!=1) or (
           f"&d_{off:x}" not in table):
            raise ValueError("real upstream did not generate requested whole function")
    # Crucial: no 'test' should pass if upstream only emitted a bail/step
    # rather than actual x86 LOCK atomic and SIMD guest memory operations.
    if emitted.count("rc_cas(")<1 or (
       emitted.count("rc_vld(")<2) or (
       emitted.count("rc_vst(")<2):
        raise ValueError("real bbrecomp failed to emit LOCK CAS AND 128/256 SIMD")
    if "rc->step(" in emitted:
        raise ValueError("generated code contains interpreter step fallback")
    print("NATIVE_V391_PINNED_GENERATED_LOCK_CAS_SIMD128_SIMD256_PASS")
    print("synthetic_functions=5; retail_game_bytes=0; original_game_boot=FALSE")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    try:make(a.upstream_checkout,a.out)
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as e:
        print(type(e).__name__+": "+str(e)[:320],file=sys.stderr)
        raise SystemExit(2)
