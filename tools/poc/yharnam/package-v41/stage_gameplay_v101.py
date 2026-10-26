#!/usr/bin/env python3
"""V101: ship verified PR17 V97/V98/V99 original game in native Windows build.

PR17 and PR20 are deliberately separate DRAFTs; source-policy tests in
PR17 DO NOT mean that PR20's EXE includes those changes. This stages
the exact already-reviewed original-game transforms into the pinned
77e3507 game checkout AFTER PR20 source overlays and BEFORE CMake.
All transforms execute in memory; no partial write if source drifts.
The authoritative game still runs on Yharnam Together / Qt shadNet.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

PIN="77e350743a7cb4524cfcc1782fb6e3af64e25b15"
SCRIPTS=(
    "patch_upstream_doll_flag_v97.py",
    "patch_upstream_lethal_catches_v98.py",
    "patch_upstream_stale_death_v99.py",
)
PATCH_DIR=Path(__file__).resolve().parent.parent/"hybrid-transport-v52"
RULES=(
    ("emulator/src/core/bloodborne_flags.h", b"Range(6700, 6700, FlagOwner::PerPlayer, 0"),
    ("emulator/src/core/bloodborne_party_death.cpp", b"run.lethal_catches.Take("),
    ("emulator/src/core/bloodborne_party_death.cpp", b"ClearStaleDeathMarks()"),
    ("emulator/src/core/bloodborne_re.cpp", b"ClearStaleDeathMarks();"),
)

def module(name: str):
    path=PATCH_DIR/name
    spec=importlib.util.spec_from_file_location("shyt_v101_"+name.replace(".","_"),path)
    if spec is None or spec.loader is None:
        raise ValueError("V101 cannot load local original-game patch: "+name)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def _lf_from_checkout(relative: str, data: bytes) -> bytes:
    """Windows Git can checkout pristine C++ text as CRLF; patch pins use LF.

    Accept *only* uniform CRLF or uniform LF, never mixed line endings or
    stray CR, so this is line-ending normalization rather than a fuzzy
    source patch that might overwrite unreviewed game changes.
    """
    crlf=data.count(b"\r\n")
    if b"\r" in data:
        if not crlf or data.count(b"\r")!=crlf or data.count(b"\n")!=crlf:
            raise ValueError("V101 unexpected/mixed original game line endings: "+relative)
        return data.replace(b"\r\n",b"\n")
    return data

def transform(original: dict[str,bytes])->dict[str,bytes]:
    """The same V97 -> V98 -> V99 ordering proven in PR17, no IO."""
    changed={name:_lf_from_checkout(name,data) for name,data in original.items()}
    for name in SCRIPTS:
        step=module(name)
        selected={}
        for relative in step.FILES:
            if relative not in changed:
                raise ValueError("V101 pinned original game missing "+relative)
            selected[relative]=changed[relative]
        changed.update(step.patch(selected))
    for relative,needle in RULES:
        if needle not in changed[relative]:
            raise ValueError("V101 original native gameplay fix missing "+relative)
    if b"run.seen_catches" in changed["emulator/src/core/bloodborne_party_death.cpp"]:
        raise ValueError("V101 old post-respawn deferred lethal queue remains")
    return changed

def stage(root:Path)->dict:
    root=root.resolve()
    actual=subprocess.check_output(
        ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if actual!=PIN:
        raise ValueError("V101 wrong pinned Yharnam Together revision "+actual)
    mods=[module(x) for x in SCRIPTS]
    all_paths=sorted({p for step in mods for p in step.FILES})
    originals={}
    for name in all_paths:
        path=root/name
        if not path.is_file() or path.is_symlink():
            raise ValueError("V101 missing or symlinked native gameplay source "+name)
        originals[name]=path.read_bytes()
    fixed=transform(originals) # all-or-nothing anchor validation BEFORE any write
    changed={k:v for k,v in fixed.items() if originals[k]!=v}
    if set(changed)!=set(all_paths):
        raise ValueError("V101 unexpected partial gameplay transform")
    # Build must actually COMPILE these patched emulator C++ files as part
    # of the native bbnet target; test the original CMake source listing.
    cmake=(root/"bbport/gpu/CMakeLists.txt").read_text(encoding="utf-8")
    for unit in ("bloodborne_re.cpp","bloodborne_party.cpp",
                 "bloodborne_party_death.cpp","bloodborne_flags_store.cpp"):
        if unit not in cmake:
            raise ValueError("V101 original GPU CMake does not compile "+unit)
    import os
    import tempfile
    pending=[]
    try:
        for name in all_paths:
            dest=root/name
            with tempfile.NamedTemporaryFile(
                mode="wb",dir=dest.parent,
                prefix=".shyt-v101-",suffix=".part",delete=False
            ) as tmp:
                tmp.write(fixed[name])
                pending.append((Path(tmp.name),dest))
        for tmp,dest in pending:
            os.replace(tmp,dest)
    finally:
        for tmp,_ in pending:
            tmp.unlink(missing_ok=True)
    digest={k:hashlib.sha256(fixed[k]).hexdigest() for k in all_paths}
    report={
        "development_only":True,"native_gameplay_direct_udp_enabled":False,
        "pinned_upstream":PIN,"patch_order":list(SCRIPTS),
        "native_game_translation_units_verified":True,
        "source_sha256":digest,
    }
    out=root/"bbport/out"
    out.mkdir(parents=True,exist_ok=True)
    (out/"shyt-v101-gameplay-source.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("SHYT_V101_ACTUAL_NATIVE_GAME_SOURCE_IN_BBNET_STAGED",len(all_paths))
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("pinned_checkout",type=Path)
    stage(parser.parse_args().pinned_checkout)
