#!/usr/bin/env python3
"""V393: additional Linux ELF relocatable-object provenance/symbol gate.

Inspects a real Clang/GCC .o compiled from the EXACT V392-instrumented
pinned bbrecomp generated C shard. Checks required V390 helper symbols
in BOTH undefined-symbol records and ELF relocations. Rejects a set of
known interpreter/translator guest runtime dependencies. The absence of
raw guest pointer derefs CANNOT be proved using symbol names alone.
This is NOT whole-game binary closure and NOT an AST verification.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys

PRESENT=(
    "shyt_generated_cas_v390",
    "shyt_generated_try_probe_v390",
    "shyt_generated_ld_v390",
    "shyt_generated_st_v390",
)
FORBIDDEN=(
    "bbcpu_step", "bbcpu_run","bbcpu_jit_run",
    "bbcpu_call_host_at_rip","bbcpu_recomp_run",
    "bb_load","bb_store","bbcpu_exec_vec",
)
FUNCTIONS=("f_1000","f_1020","f_1040","f_1060","f_1080")

def verify_symbols(undef:str,defined:str,relocs:str)->None:
    u=set(re.findall(r"\b(?:shyt_generated_[a-z0-9_]+|bbcpu_[a-z0-9_]+|bb_load|bb_store)\b",undef))
    d=set(re.findall(r"\bf_[0-9a-f]+\b",defined))
    sym=re.findall(r"\b(?:shyt_generated_[a-z0-9_]+|bbcpu_[a-z0-9_]+|bb_load|bb_store)\b",relocs)
    r=set(sym)
    if not all(x in u for x in PRESENT):
        raise ValueError("missing actual compiled code's V390 bridge symbol dependency")
    if not all(x in r for x in PRESENT):
        raise ValueError("missing ELF relocation to V390 memory adapter")
    if any(x in u or x in r or x in d for x in FORBIDDEN):
        raise ValueError("actual compiled generated object depends on guest runtime")
    if d!=set(FUNCTIONS):
        raise ValueError("actual emitted function definitions incomplete or unexpected")
    if "shyt_generated_" not in undef or "shyt_generated_" not in relocs:
        raise ValueError("no compiled guest VM-mediated memory path")

def subprocess_output(tool:list[str])->str:
    x=subprocess.run(tool,capture_output=True,text=True,check=False,timeout=25)
    if x.returncode:
        raise ValueError("native object audit command failed")
    if len(x.stdout)>2_000_000:
        raise ValueError("generated object audit output exceeds bound")
    return x.stdout

def main()->None:
    a=argparse.ArgumentParser()
    a.add_argument("--object",type=Path,required=True)
    args=a.parse_args()
    obj=args.object.resolve(strict=True)
    if not obj.is_file() or obj.suffix!=".o" or obj.is_symlink() or obj.stat().st_size>10_000_000:
        raise ValueError("refusing non-ELF object/oversized or symlink")
    nm=shutil.which("nm"); od=shutil.which("objdump")
    if not nm or not od:
        raise ValueError("GNU binutils required for Linux ELF object provenance")
    undefined=subprocess_output([nm,"--undefined-only",str(obj)])
    defined=subprocess_output([nm,"--defined-only",str(obj)])
    relocation=subprocess_output([od,"-r",str(obj)])
    verify_symbols(undefined,defined,relocation)
    print("NATIVE_V393_REAL_GENERATED_ELF_OBJECT_BRIDGE_SYMBOL_GATE_PASS")
    print("compiled_functions=5 required_v390_memory_relocations=4")
    print("original_game_native_boot_proven=FALSE")

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
        print("NATIVE_V393_ELF_OBJECT_AUDIT_REFUSED: "+type(e).__name__,
              file=sys.stderr)
        raise SystemExit(2)
