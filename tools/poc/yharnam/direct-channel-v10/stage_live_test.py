#!/usr/bin/env python3
"""Build a V10 test tree from the immutable V7 archive, never in-place."""
import argparse
import hashlib
from pathlib import Path
import zipfile
from guard_adapter import patch_adapter
PIN_SHA256="e2818139c1001cd61ab10c4e6aef70c67b131be00ea1f7fb0fb3aefef1985559"
def stage(v7:Path,source:Path,out:Path):
    if out.resolve()==source.resolve() or source.resolve() in out.resolve().parents:
        raise ValueError("never write inside the source directory")
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("destination is not empty")
    if hashlib.sha256(v7.read_bytes()).hexdigest()!=PIN_SHA256:
        raise ValueError("pinned V7 archive digest mismatch")
    with zipfile.ZipFile(v7) as zipped:
        original=zipped.read("native_shlk_adapter.hpp").decode("utf-8")
        header=zipped.read("native_shlk_direct.hpp")
    guarded=patch_adapter(original).encode("utf-8")
    files={
        "native_shlk_direct.hpp":header,
        "native_shlk_adapter.hpp":guarded,
    }
    for name in ("native_direct_filter.hpp","test_direct_filter.cpp",
                 "test_guard_live.cpp","CMakeLists.txt"):
        files[name]=(source/name).read_bytes()
    out.mkdir(parents=True,exist_ok=True)
    for name,data in files.items():
        (out/name).write_bytes(data)
    print("V10_STAGE_PASS",len(files),"verified input files")
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--v7",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    stage(args.v7,args.source,args.out)
