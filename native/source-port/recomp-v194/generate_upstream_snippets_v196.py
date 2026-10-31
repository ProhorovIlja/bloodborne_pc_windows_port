#!/usr/bin/env python3
"""V196: run original bbrecomp --snippets with invented x86-64 instruction input.

Game dumps, PS4 eboot, derived private code and proprietary assets are NEVER
accepted as CLI input. Real upstream generated C is emitted to a CI temporary
folder (never staged into GitHub). This strictly synthetic fixture is not
proof of actual Bloodborne native Win64 game-code compilation.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

UPSTREAM="8f31ec7c41f252730c6325d52647046baef7549f"
GENERATOR_BLOB="f5032c9ead4988579e005af8a0a0ce4ba4ab66d8"
BODY=(
    "4889f8",        # mov rax,rdi
    "4801f0",        # add rax,rsi
    "31c0",          # xor eax,eax
    "48ffc0",        # inc rax
    "48c7c001000000" # mov rax,1
)
EXPECT=("s_1","s_2","s_3","s_4","s_5")
PROHIBITED=(
    "rc->step(", "rc->call(", "rc->tail(", "rc->bail(",
    "bbcpu_", "eboot.bin", "PS4", "Orbis",
)
def sha_blob(content:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()

def validate_generated(text:str)->dict:
    for sym in EXPECT:
        if text.count("static void "+sym+"(BbCpu *c) {")!=1:
            raise ValueError("not all five upstream instructions compiled as native C")
    if "static const RcFunction table[]" not in text or (
        text.count("const RcFunction *bb_recomp_init(")!=1
    ):
        raise ValueError("upstream generated C API or table missing")
    for sym in EXPECT:
        if text.count(","+sym+"}")!=1:
            raise ValueError("unexpected generated snippet metadata")
    if any(token in text for token in PROHIBITED):
        raise ValueError("generated C requires forbidden interpreter/HLE callbacks")
    return {
        "exact_upstream_generated_snippets":len(EXPECT),
        "no_ps4_eboot_runtime_dependency_in_generated_test":True,
        "native_game_code_proven":False
    }

def generate(root:Path,out:Path)->dict:
    root=root.resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                               text=True,stderr=subprocess.DEVNULL).strip()!=UPSTREAM:
        raise ValueError("upstream recomp generator commit drift")
    source=subprocess.check_output(["git","-C",str(root),"show",
                                    "HEAD:tools/recomp/bbrecomp.c"])
    if sha_blob(source)!=GENERATOR_BLOB:
        raise ValueError("upstream recomp generator source blob drift")
    compiler=root/"out/recomp/bbrecomp"
    if not compiler.is_file():
        raise ValueError("original upstream bbrecomp not compiled")
    if out.exists() or not out.parent.is_dir() or out.parent.is_symlink():
        raise ValueError("generated C must be written to a new CI scratch path")
    for p in (out.parent,*out.parent.parents):
        if (p/".git").exists():
            raise ValueError("generated C must be outside all git worktrees")
    inp=out.parent/"native-v196-invented-instructions.txt"
    if inp.exists():raise ValueError("input scratch path already exists")
    inp.write_text("\n".join(BODY)+"\n",encoding="ascii")
    p=subprocess.run([str(compiler),"--snippets",str(inp),str(out)],
                     cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     timeout=120,check=False)
    if p.returncode:
        # This is a synthetic fixture. Output stays bounded in CI.
        raise RuntimeError("original upstream recompiler failed to generate C")
    if not out.is_file() or out.stat().st_size>2_000_000:
        raise ValueError("missing or unexpectedly large generated C")
    result=validate_generated(out.read_text(encoding="utf-8"))
    print("SHYT_V196_ACTUAL_UPSTREAM_BBRECOMP_SYNTHETIC_GENERATION_PASS")
    print(result)
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:generate(args.upstream_checkout,args.out)
    except (ValueError,RuntimeError,OSError,subprocess.CalledProcessError) as e:
        print(type(e).__name__+": "+str(e)[:180],file=sys.stderr)
        raise SystemExit(2)
