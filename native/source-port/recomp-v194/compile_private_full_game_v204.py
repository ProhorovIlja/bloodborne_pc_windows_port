#!/usr/bin/env python3
"""V204 private generated whole-game function-C -> Windows AMD64 COFF.

Run on NATIVE Windows, after Linux/WSL original executable preparation.
Requires the SAME private WORK directory (with generated C and manifest).
Strict default rejects interpreter/PS4 guest runtime callback dependencies.
Use --research-only to compile diagnostic object files without claiming a
standalone, working Bloodborne.exe. Never upload generated C/COFF or EBOOT.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import audit_native_runtime_v202 as audit
import build_incremental_coff_v198 as coff
from prepare_private_full_game_v204 import PIN,STAMP,sha,private

def build(root:Path,work:Path,jobs:int,research:bool)->dict:
    work=private(work)
    if not work.is_dir():
        raise ValueError("prepare private original game executable first on WSL2")
    if jobs<1 or jobs>8:
        raise ValueError("Windows native compilation workers must be 1..8")
    metadata=work/"full-original-preparation.json"
    if not metadata.is_file() or metadata.is_symlink():
        raise ValueError("private original game function manifest missing")
    manifest=json.loads(metadata.read_text(encoding="utf-8"))
    if manifest.get("format")!=STAMP or manifest.get("upstream")!=PIN:
        raise ValueError("unrecognized private complete-game source manifest")
    root=root.resolve(strict=True)
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                stderr=subprocess.DEVNULL,text=True).strip()
    if rev!=PIN:
        raise ValueError("original code generator source pin mismatch")
    generated=private(work/"generated")
    files=audit.sources(generated)
    hashes={p.name:sha(p) for p in files}
    if hashes!=manifest.get("c_hashes"):
        raise ValueError("full original-game generated C differs from manifest")
    status=audit.audit(generated)
    if not research and not status["strict_native_runtime_ready"]:
        raise ValueError("STRICT native Windows build blocked: original generated "
                         "code still calls legacy guest CPU/runtime; "
                         "research-only COFF is allowed, playable game is NOT")
    # Reuses the real source-locked V198 Windows clang-cl pipeline; SHA-256
    # for every object and every source is checked before any reuse.
    results=coff.build(root,generated,work/"win64-coff",None,jobs,None,
                       require_no_guest_runtime=not research)
    return {"scope":"entire private prepared original executable",
            "research_only":research,
            "functions_scanned":manifest["functions_scanned"],
            "windows_amd64_coff_objects":results["source_count"],
            "objects_compiled":results["compiled"],
            "objects_reused":results["reused"],
            "legacy_guest_callback_sites":status["callback_total"],
            "strict_native_runtime_ready":status["strict_native_runtime_ready"],
            "original_version_109_verified":manifest["version_109_verified"],
            "real_game_windows_pe_linked":False,
            "game_boot_proven":False}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",required=True,type=Path)
    p.add_argument("--work",required=True,type=Path)
    p.add_argument("--jobs",type=int,default=2)
    p.add_argument("--research-only",action="store_true")
    args=p.parse_args()
    try:
        r=build(args.upstream,args.work,args.jobs,args.research_only)
        print("SHYT_V204_FULL_PRIVATE_GAME_WIN64_COFF_PREPARATION_PASS")
        print(json.dumps(r,sort_keys=True))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError,
            json.JSONDecodeError) as e:
        print("SHYT_V204_WIN64_PRIVATE_AOT_BLOCKED: "+str(e)[:220],
              file=sys.stderr)
        raise SystemExit(2)
