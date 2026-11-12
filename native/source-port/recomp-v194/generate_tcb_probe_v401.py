#!/usr/bin/env python3
"""V401: real PINNED public bbrecomp compilation of 12 invented functions,
including FS/GS TCB MOV variants and an FS nonzero-offset negative control.

Creates a second independent disposable ELF64/actual RcFunction table
under runner temp. Does NOT alter seven-function V400/V399 source
manifest, runtime CALL RAX route or any owner original game bytes.
"""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location(
    "v395_invented",ROOT/"generate_verified_imports_v395.py")
assert spec and spec.loader
v395=importlib.util.module_from_spec(spec)
spec.loader.exec_module(v395)

TCB=(
 (0x10e0,bytes.fromhex("64488b042500000000c3"),"mov_rax_fs_absolute_zero_ret"),
 (0x1100,bytes.fromhex("65488b042540000000c3"),"mov_rax_gs_absolute_40_ret"),
 (0x1120,bytes.fromhex("64488b1c2500000000c3"),"mov_rbx_fs_absolute_zero_ret"),
 (0x1140,bytes.fromhex("64488b042540000000c3"),"mov_rax_fs_absolute_40_negative_ret"),
 (0x1160,bytes.fromhex("65488b1c2540000000c3"),"mov_rbx_gs_absolute_40_ret")
)
FUNCTIONS=v395.FUNCTIONS+TCB

def build_elf()->bytes:
    elf=bytearray(v395.build_elf())
    for off,body,_ in TCB:
        assert off>=0x1000 and off+len(body)<=len(elf)
        elf[off:off+len(body)]=body
    return bytes(elf)

def generate(checkout:Path,out:Path)->None:
    root=checkout.resolve(strict=True)
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
        text=True,stderr=subprocess.DEVNULL).strip()
    src=subprocess.check_output(["git","-C",str(root),"show",
        "HEAD:tools/recomp/bbrecomp.c"],stderr=subprocess.DEVNULL)
    if rev!=v395.PINNED or v395.blobhash(src)!=v395.GENERATOR_BLOB:
        raise ValueError("untrusted pinned public bbrecomp compiler")
    exe=root/"out/recomp/bbrecomp"
    if not exe.is_file() or out.exists() or not out.parent.is_dir() or (
       out.parent.is_symlink()):
        raise ValueError("offline compiler or fresh runner output missing")
    if any((p/".git").exists() for p in (out.parent,*out.parent.parents)):
        raise ValueError("cannot write generated code into source checkout")
    scratch=out.parent
    image=scratch/"V401_INVENTED_FS_GS_TCB_NOT_BLOODBORNE.elf"
    tsv=scratch/"functions.tsv"
    offsets=scratch/"function_offsets.txt"
    if image.exists() or tsv.exists() or offsets.exists():
        raise ValueError("refuse to overwrite source attestation inputs")
    image.write_bytes(build_elf())
    tsv.write_text("start\tsize\tinsns\tundecodable\n"+
        "".join(f"0x{off:016x}\t{len(body)}\t2\t0\n"
                for off,body,_ in FUNCTIONS),encoding="ascii")
    offsets.write_text("".join(f"0x{off:x}\n" for off,_,_ in FUNCTIONS),
                       encoding="ascii")
    run=subprocess.run([str(exe),str(image),str(tsv),str(out),
        "@"+str(offsets)],cwd=root,stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,timeout=120)
    if run.returncode:
        raise ValueError("PINNED_BBRECOMP_REFUSED_12_INVENTED_FUNCTIONS: "+
            (run.stderr or run.stdout)[-420:].decode(errors="replace"))
    shard=out.with_name(out.stem+"_00000.c")
    if not out.is_file() or not shard.is_file() or (
        out.stat().st_size+shard.stat().st_size>2_000_000):
        raise ValueError("pinned compiler did not emit 12-function source")
    a=out.read_text(encoding="utf-8")
    b=shard.read_text(encoding="utf-8")
    for off,_,_ in FUNCTIONS:
        if a.count(f"void f_{off:x}(BbCpu *c);")!=1 or (
            b.count(f"void f_{off:x}(BbCpu *c) {{")!=1) or (
            a.count(f"&d_{off:x}")!=1):
            raise ValueError("12-function source and native slot coverage failed")
    # The FS:[nonzero] control is intentionally NOT supported by
    # pinned bbrecomp: it emits rc->step, proving that promoting the
    # entire 12-function probe would violate native-only execution.
    # We inspect it only as a BUILD-TIME negative and never publish,
    # compile into a runtime guest image or execute that callback.
    import re
    matches=list(re.finditer(r"void f_([0-9a-f]+)\(BbCpu \*c\) \{",b))
    if len(matches)!=len(FUNCTIONS):
        raise ValueError("incomplete generated function scope inventory")
    direct_tcb=0
    quarantined=0
    for i,m in enumerate(matches):
        off=int(m.group(1),16)
        end=matches[i+1].start() if i+1<len(matches) else len(b)
        body=b[m.end():end]
        if off==0x1140:
            if "c->tcb" in body or "rc->step(" not in body:
                raise ValueError("FS nonzero control unexpectedly native or hidden")
            quarantined+=1
        elif off in (0x10e0,0x1100,0x1120,0x1160):
            if "c->tcb" not in body or "rc->step(" in body:
                raise ValueError("eligible FS/GS TCB load not native-only")
            direct_tcb+=1
        elif "rc->step(" in body:
            raise ValueError("ordinary invented function contains interpreter STEP")
    if direct_tcb!=4 or quarantined!=1:
        raise ValueError("TCB native/quarantined source scopes incomplete")
    print("NATIVE_V401_PINNED_GENERATED_12_FUNCTION_TCB_C_SOURCE_PASS")
    print("synthetic_TCB_native_sites=4 FS_nonzero_interpreter_fallback_QUARANTINED=1 retail_Bloodborne=0")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream-checkout",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    try:generate(args.upstream_checkout,args.out)
    except (ValueError,OSError,RuntimeError,subprocess.CalledProcessError) as e:
        print("V401_TCB_GENERATE_REFUSED: "+type(e).__name__+": "+str(e)[:400],
              file=sys.stderr)
        raise SystemExit(2)
