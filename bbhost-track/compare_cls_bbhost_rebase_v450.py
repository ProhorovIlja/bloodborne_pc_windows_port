#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V450: compare actual CLS bbhost v1.4.0 public release against BBHost old and 0.2.26.

Examines exact source-only archive, never merges or executes it.
Source deltas and git-apply compatibility are diagnostic; a successful hunk
check alone NEVER establishes gameplay correctness or binary ABI parity.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

EXPECTED_ZIP = "7c00d46f01b67ff1cf12cef346c245960b627141a9c1047d00e2ceadd167ca04"
BASE = "8d8f07db3bad61dcdbf11511c9d34acfdfa162cd"
MODERN = "bdc5cdf8be5f37188da9c2368e92be444fdc04cb"
PREFIX = "YharnamTogether-v1.4.0-bbhost-source/"
MAX_MEMBERS=40000
MAX_FILE=1024*1024
EXT={".h",".hpp",".cpp",".c",".cc",".cmake",".txt"}
EXTRACT={
    "CMakeLists.txt":"CMakeLists.txt",
    "cmake/bbsc_yt.cmake":"bbsc_yt.cmake",
    "tools/bbsc/README-BBSC.txt":"README-BBSC.txt",
    "tools/bbsc/clang64-toolchain.cmake":"clang64-toolchain.cmake",
    "SOURCE-COMMIT.txt":"RELEASE-SOURCE-COMMIT.txt",
}
def git(root: Path, *args: str) -> str:
    r=subprocess.run(["git","-C",str(root),*args],text=True,capture_output=True,timeout=15)
    if r.returncode:
        raise ValueError("original Git SHA verification unavailable")
    return r.stdout.strip()

def run(archive:Path,base:Path,modern:Path,artifact:Path) -> dict:
    if archive.is_symlink() or not archive.is_file() or archive.stat().st_size>32*1024*1024:
        raise ValueError("not a bounded public release archive")
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=EXPECTED_ZIP:
            raise ValueError("source archive digest drift")
    if git(base,"rev-parse","HEAD")!=BASE or git(modern,"rev-parse","HEAD")!=MODERN:
        raise ValueError("base/modern exact Git SHA drift")
    result={"schema":"SHYT_V450_REAL_CLS_RELEASE_REBASE_SURVEY","release_sha256":EXPECTED_ZIP,
            "upstream_parent_sha":BASE,"modern_candidate_sha":MODERN,
            "changed_existing":[],"new_source":[],"unchanged_existing":0,
            "missing_from_release":[],"limitations":"source-only diff check, no ABI or real game playability"}
    original_paths=set(git(base,"ls-files").splitlines())
    modern_paths=set(git(modern,"ls-files").splitlines())
    shipped=set()
    with zipfile.ZipFile(archive) as z:
        files=z.infolist()
        if len(files)>MAX_MEMBERS:raise ValueError("oversized archive index")
        for entry in files:
            name=entry.filename.replace("\\","/")
            if not name.startswith(PREFIX) or entry.is_dir():continue
            path=name[len(PREFIX):]
            if not path or path.startswith("/") or ".." in Path(path).parts or ":" in path:
                raise ValueError("unsafe source path")
            if path in shipped:raise ValueError("duplicate source path")
            shipped.add(path)
            if entry.file_size>MAX_FILE:continue
            if path in EXTRACT:
                artifact.mkdir(parents=True,exist_ok=True)
                (artifact/EXTRACT[path]).write_bytes(z.read(entry))
            if not (path=="CMakeLists.txt" or Path(path).suffix in EXT):
                continue
            if path not in original_paths:
                result["new_source"].append(path)
                continue
            src=(base/path).read_bytes()
            dest=z.read(entry)
            if src==dest:
                result["unchanged_existing"]+=1
                continue
            item={"path":path,"shipped_bytes":len(dest),"upstream_bytes":len(src),
                  "upstream_blob":git(base,"rev-parse","HEAD:"+path),
                  "modern_blob":git(modern,"rev-parse","HEAD:"+path) if path in modern_paths else None}
            if (len(src)>MAX_FILE or b"\x00" in src or b"\x00" in dest):
                item["apply_check"]="skipped_large_or_binary"
            else:
                old=src.decode("utf-8",errors="replace").splitlines(keepends=True)
                new=dest.decode("utf-8",errors="replace").splitlines(keepends=True)
                patch="".join(difflib.unified_diff(old,new,
                         fromfile="a/"+path,tofile="b/"+path,n=3))
                if path in {"src/engine/frame_rate.cpp","src/core/elf.cpp","src/main.cpp",
                            "src/hle/system.cpp","src/host/window.cpp","CMakeLists.txt"}:
                    outdir=artifact/"v451-port-hunks"
                    outdir.mkdir(parents=True,exist_ok=True)
                    (outdir/(path.replace("/","_")+".patch")).write_text(patch,encoding="utf-8")
                item["diff_lines"]=sum(a[0] in "+-" for a in patch.splitlines()
                                       if a and not a.startswith(("+++","---")))
                if not item["modern_blob"]:
                    item["apply_check"]="path_missing_modern"
                elif len(patch)>500000:
                    item["apply_check"]="patch_too_large"
                else:
                    # git apply --check is nonmutating. Use only 1 verified path at a time.
                    r=subprocess.run(["git","apply","--check","-"],
                        cwd=modern,input=patch,text=True,capture_output=True,timeout=15)
                    item["apply_check"]="context_ok_only" if r.returncode==0 else "requires_manual_rebase"
            result["changed_existing"].append(item)
        result["missing_from_release"]=sorted(
            p for p in original_paths-shipped if
            p.startswith(("src/","cmake/")) and p.endswith((".cpp",".h",".c",".cmake")))[:50]
    if not (artifact/"bbsc_yt.cmake").is_file() or not (artifact/"CMakeLists.txt").is_file():
        raise ValueError("actual original YT build manifest absent")
    result["changed_existing"].sort(key=lambda x:x["path"])
    result["new_source"].sort()
    result["counts"]={
        "changed_existing":len(result["changed_existing"]),
        "new_sources":len(result["new_source"]),
        "same_as_old":result["unchanged_existing"],
        "safe_context_only":sum(x.get("apply_check")=="context_ok_only" for x in result["changed_existing"]),
        "need_rebase":sum(x.get("apply_check")=="requires_manual_rebase" for x in result["changed_existing"]),
    }
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("archive","base","modern","report","artifact"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    r=run(a.archive,a.base,a.modern,a.artifact)
    a.report.write_text(json.dumps(r,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SHYT_V450_RELEASE_V140_BBHOST_026_SOURCE_DELTA_VALID")
    print("V450_COUNTS",json.dumps(r["counts"]))
    print("V450_EXISTING",json.dumps([
       {"p":x["path"],"status":x["apply_check"],"changed":x.get("diff_lines")}
       for x in r["changed_existing"][:30]]))
    print("V450_NEW",json.dumps(r["new_source"][:30]))
    print("SHYT_V450_NO_MERGE_NO_PROPRIETARY_BINARY_NO_PRODUCTION")

if __name__=="__main__":
    main()
