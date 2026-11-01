#!/usr/bin/env python3
"""V204: private, original full-game ELF -> full native function-C preparation.
Run on Linux/WSL2 only. Uses the player's decrypted EBOOT as build input,
never GitHub CI or a runtime game dependency. This is NOT game boot.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import audit_native_runtime_v202 as auditor

PIN="8f31ec7c41f252730c6325d52647046baef7549f"
STAMP="SHYT_PRIVATE_FULL_IMAGE_V204"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def private(p):
    p=p.absolute()
    if p.is_symlink() or any((a/".git").exists() for a in (p,*p.parents)):
        raise ValueError("private game files must stay outside Git worktrees")
    return p

def upstream(root):
    root=root.resolve(strict=True)
    head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                 text=True,stderr=subprocess.DEVNULL).strip()
    if head!=PIN:raise ValueError("original recomp source SHA changed")
    for tool in ("ps4elf.py","pointers.py","imports.py","import_names.inc"):
        if not (root/"tools/recomp"/tool).is_file():
            raise ValueError("missing original source-recomp executable analyzer")
    for exe in ("scan","bbrecomp"):
        if not (root/"out/recomp"/exe).is_file():
            raise ValueError("original full scanner/recompiler must be built on Linux")
    src=(root/"tools/recomp/bbrecomp.c").read_text(encoding="utf-8")
    for marker in ("SHYT_NATIVE_V199_GUEST_RET_FLAGS_FLUSH",
                   "SHYT_NATIVE_V200_INDIRECT_CALL_NATIVE_DISPATCH",
                   "SHYT_NATIVE_V201_INDIRECT_JMP_NATIVE_DISPATCH",
                   "SHYT_NATIVE_V203_GENERIC_TAIL_DIRECT_AOT"):
        if marker not in src:raise ValueError("pinned full native generator patch missing")
    return root

def run(cmd,step,env=None):
    # Never print proprietary text, symbols, paths, or original game bytes.
    result=subprocess.run([str(x) for x in cmd],capture_output=True,
                          env=env,timeout=7200)
    if result.returncode:raise RuntimeError("private stage failed: "+step)

def prepare(root,eboot,work):
    if not sys.platform.startswith("linux"):
        raise ValueError("run original scanner/generator only under Linux or WSL2")
    root=upstream(root)
    eboot=private(eboot)
    work=private(work)
    if not eboot.is_file():raise ValueError("decrypted original eboot.bin missing")
    size=eboot.stat().st_size
    if not 1000000<=size<=512*1024*1024:
        raise ValueError("executable size is invalid for original game")
    with eboot.open("rb") as f:magic=f.read(4)
    if magic not in (b"\x7fELF",b"O\x15=\x1d"):
        raise ValueError("original PS4 SELF/plain ELF header required; no encrypted dump")
    if work.exists() and any(work.iterdir()):
        raise ValueError("private output is not empty; use a new work folder")
    work.mkdir(parents=True,exist_ok=True)
    scan=work/"scan"; gen=work/"generated"
    scan.mkdir();gen.mkdir()
    t=root/"tools/recomp"
    elf=work/"original.elf"
    original=eboot.resolve(strict=True)
    run([sys.executable,t/"ps4elf.py",original,elf],"extract ELF")
    run([sys.executable,t/"pointers.py",original,scan/"pointers.txt"],"pointers")
    run([root/"out/recomp/scan",elf,scan,scan/"pointers.txt"],"function scan")
    tab=scan/"functions.tsv"
    count=0;prev=-1
    with tab.open(encoding="utf-8") as f, (scan/"all.txt").open("w") as out:
        if f.readline().strip()!="start\tsize\tinsns\tundecodable":
            raise ValueError("original full scanner's function format changed")
        for line in f:
            row=line.strip().split("\t")
            if len(row)!=4:raise ValueError("original function row invalid")
            addr=int(row[0],16)
            if addr<=prev or int(row[1])<=0:
                raise ValueError("original function index invalid")
            out.write(row[0]+"\n")
            prev=addr;count+=1
            if count>1000000:raise ValueError("original function count exceeds safety bound")
    if not count:raise ValueError("original scanner discovered no function")
    run([sys.executable,t/"imports.py",original,scan],"original imports")
    annotations=root/"annotations/functions.tsv"
    if not annotations.is_file():raise ValueError("upstream annotations missing")
    env={**os.environ,"BB_JIT":"0",
         "BB_RECOMP_ANNOTATIONS":str(annotations)}
    run([root/"out/recomp/bbrecomp",elf,tab,gen/"recomp.c",
         "@"+str(scan/"all.txt")],"full original function generation",env)
    hashes={p.name:sha(p) for p in auditor.sources(gen)}
    audit=auditor.audit(gen)
    metadata={"format":STAMP,"upstream":PIN,
              "input_sha256":sha(original),"original_size_bytes":size,
              "version_109_verified":False,
              "functions_scanned":count,"c_hashes":hashes,
              "fallback_calls":audit["callback_total"],
              "strict_no_guest_runtime":audit["strict_native_runtime_ready"],
              "native_game_boot_proven":False}
    stage=work/"full-original-preparation.json.partial"
    stage.write_text(json.dumps(metadata,sort_keys=True,indent=2)+"\n")
    os.replace(stage,work/"full-original-preparation.json")
    elf.unlink()
    return {"functions_scanned":count,"generated_c_modules":len(hashes),
            "fallback_calls":audit["callback_total"],
            "strict_no_guest_runtime":audit["strict_native_runtime_ready"],
            "version_109_verified":False,"game_boot_proven":False}

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--upstream",required=True,type=Path)
    a.add_argument("--eboot",required=True,type=Path)
    a.add_argument("--work",required=True,type=Path)
    o=a.parse_args()
    try:
        result=prepare(o.upstream,o.eboot,o.work)
        print("SHYT_V204_FULL_PRIVATE_ORIGINAL_GAME_C_GENERATION_PASS")
        print(json.dumps(result,sort_keys=True))
    except (ValueError,OSError,RuntimeError,subprocess.SubprocessError) as e:
        print("SHYT_V204_PRIVATE_FULL_IMAGE_BLOCKED: "+str(e)[:180],file=sys.stderr)
        raise SystemExit(2)
