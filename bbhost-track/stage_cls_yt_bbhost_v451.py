#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V451: stage real CLS YT v1.4.0 BBHost game hooks on BBHost 0.2.26 in CI ONLY.

The published CLS complete-source archive is exact-SHA pinned and its original
BBHost parent is exact pinned. Nine original source deltas are applied via git;
the one changed frame_rate.cpp context is adapted without overwriting modern
BBHost timing fixes. New src/yt sources and CMake integration come ONLY from
the published CLS source archive. NEVER modifies the GitHub repo, real Fornex,
installed user client/game files, accounts, or save data.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from compare_cls_bbhost_rebase_v450 import BASE, MODERN, EXPECTED_ZIP, PREFIX

CHANGED = (
    "CMakeLists.txt",
    "src/core/elf.cpp",
    "src/engine/frame_rate.cpp",
    "src/hle/audio.cpp",
    "src/hle/fs.cpp",
    "src/hle/pthread.cpp",
    "src/hle/system.cpp",
    "src/host/window.cpp",
    "src/main.cpp",
    "third_party/imgui/imconfig.h",
)
NEW = (
    "cmake/bbsc_yt.cmake",
    "src/yt/shim/video_core/renderer_vulkan/vk_instance.h",
    "src/yt/shim/video_core/renderer_vulkan/vk_scheduler.h",
    "src/yt/yt_gpu.cpp",
    "src/yt/yt_host.cpp",
    "src/yt/yt_host.h",
    "src/yt/yt_nids.inc",
    "src/yt/yt_ui.cpp",
    "src/yt/yt_ui.h",
    "third_party/imgui/VERSION.txt",
    "tools/bbsc/README-BBSC.txt",
    "tools/bbsc/clang64-toolchain.cmake",
)
EXPECTED_MODERN_FRAMERATE = "5fe35eac7b10ad9b8e20258272d73cb3193185fc"
ORIGINAL_FRAME = '''    if (const char* e = std::getenv("BBHOST_GAME_FPS"); e && *e) return mode_of(std::atoi(e));
    return mode_of(host_settings().frame_cap);
'''
RELEASE_FRAME = '''    if (const char* e = std::getenv("BBHOST_GAME_FPS"); e && *e) return mode_of(std::atoi(e));
    int cap = host_settings().frame_cap;
    // BBSC: co-op plays at 60, or up to 120 unlocked: above that the others freeze and fly.
    if (const char* online = std::getenv("BB_ONLINE"); online && online[0] == '1') {
        const char* unlocked = std::getenv("BB_ONLINE_UNLOCKED_FPS");
        const int most = unlocked && unlocked[0] == '1' ? 120 : 60;
        if (cap <= 0 || cap > most) cap = most;
    }
    return mode_of(cap);
'''

def checked_git(root:Path,*args:str,input:str|None=None)->str:
    p=subprocess.run(["git","-C",str(root),*args],input=input,text=True,
                     capture_output=True,timeout=30)
    if p.returncode:
        raise ValueError("exact source patch failed: "+ " ".join(args[:3]))
    return p.stdout.strip()

def stage(archive:Path,parent:Path,modern:Path)->dict:
    if (archive.is_symlink() or archive.stat().st_size>32*1024*1024
            or not archive.is_file()):
        raise ValueError("unexpected public source archive")
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=EXPECTED_ZIP:
            raise ValueError("CLS source archive drift")
    if checked_git(parent,"rev-parse","HEAD")!=BASE:
        raise ValueError("parent BBHost commit drift")
    if checked_git(modern,"rev-parse","HEAD")!=MODERN:
        raise ValueError("modern BBHost commit drift")
    if checked_git(modern,"status","--porcelain"):
        raise ValueError("source host checkout not clean")
    if checked_git(modern,"rev-parse","HEAD:src/engine/frame_rate.cpp")!=EXPECTED_MODERN_FRAMERATE:
        raise ValueError("modern frame timing implementation drift")

    with zipfile.ZipFile(archive) as z:
        archive_names = {x.filename.replace("\\","/") for x in z.infolist() if not x.is_dir()}
        if len(archive_names)>40000:
            raise ValueError("archive file count out of bounds")
        manifest=PREFIX+"SOURCE-COMMIT.txt"
        if manifest not in archive_names:
            raise ValueError("CLS release provenance missing")
        stamp=z.read(manifest).decode("utf-8")
        if ("efa0ad265d840d9195e55db2e3216f46f7daedd0" not in stamp
                or "v1.4.0" not in stamp):
            raise ValueError("wrong YT version embedded in release provenance")
        wanted=set(CHANGED)|set(NEW)
        for name in wanted:
            if PREFIX+name not in archive_names:
                raise ValueError("CLS source member missing: "+name)

        applied=[]
        for path in CHANGED:
            raw=z.read(PREFIX+path)
            if len(raw)>1024*1024 or b"\x00" in raw:
                raise ValueError("unexpected binary source in code port")
            src=(parent/path).read_bytes()
            orig=src.decode("utf-8")
            released=raw.decode("utf-8")
            target=modern/path
            if path=="src/engine/frame_rate.cpp":
                now=target.read_text(encoding="utf-8")
                if (orig.count(ORIGINAL_FRAME)!=1 or released.count(RELEASE_FRAME)!=1
                        or now.count(ORIGINAL_FRAME)!=1):
                    raise ValueError("frame limit or modern frame timing seam drift")
                target.write_text(now.replace(ORIGINAL_FRAME,RELEASE_FRAME,1),encoding="utf-8")
                applied.append({"file":path,"method":"explicit_exact_framecap_rebase"})
            else:
                patch="".join(difflib.unified_diff(
                    orig.splitlines(keepends=True),released.splitlines(keepends=True),
                    fromfile="a/"+path,tofile="b/"+path,n=3))
                if not patch:
                    raise ValueError("unexpected empty CLS source patch: "+path)
                checked_git(modern,"apply","--check","-",input=patch)
                checked_git(modern,"apply","-",input=patch)
                applied.append({"file":path,"method":"original_release_unified_diff"})
        for name in NEW:
            dest=modern/name
            if dest.exists() or dest.is_symlink():
                raise ValueError("destination already has CLS-specific source: "+name)
            info=z.getinfo(PREFIX+name)
            if info.file_size>1024*1024:
                raise ValueError("unexpected new-source size")
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(z.read(info))
        if 'include(cmake/bbsc_yt.cmake)' not in (modern/'CMakeLists.txt').read_text():
            raise ValueError("real complete game host CMake integration not installed")
        if 'bbcoop_install(' not in (modern/'src/yt/yt_host.cpp').read_text():
            raise ValueError("real game engine hook loader not installed")
        if 'add_library(bbnet STATIC' not in (modern/'cmake/bbsc_yt.cmake').read_text():
            raise ValueError("real YT network/game sources absent")
        for filename in CHANGED:
            if (modern/filename).read_bytes()==(parent/filename).read_bytes():
                raise ValueError("CLS source patch unexpectedly not applied")
    changed=checked_git(modern,"status","--porcelain").splitlines()
    if len(changed) != len(CHANGED)+len({p.split("/")[0] for p in NEW if p.startswith(("src/yt","tools/bbsc","cmake/"))})+1:
        # Versioned changes count and untracked directories have implementation-
        # dependent grouping: don't use a brittle assertion here.
        if len(changed)<len(CHANGED):
            raise ValueError("staged host modifications missing")
    checked_git(modern,"diff","--check")
    return {"schema":"SHYT_V451_REAL_CLS_140_BBHOST_026_STAGED",
            "cls_zip_sha256":EXPECTED_ZIP,"original_bbhost":BASE,"modern_bbhost":MODERN,
            "yt_source":"efa0ad265d840d9195e55db2e3216f46f7daedd0",
            "source_patches":applied,"new_public_source":list(NEW),
            "proof_only":"source staging + context checks; not game boot, link or release"}

def main()->None:
    p=argparse.ArgumentParser()
    for name in ("archive","parent","modern","report"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    report=stage(a.archive,a.parent,a.modern)
    a.report.write_text(json.dumps(report,indent=2)+"\n")
    print("SHYT_V451_ACTUAL_CLS_GAME_HOOK_BBHOST_026_REBASE_STAGED")
    print("SHYT_V451_CHANGED",len(report["source_patches"]),"NEW",len(report["new_public_source"]))
    print("SHYT_V451_RELEASE_NEVER_DEPLOYED_NO_GAME_BINARY")

if __name__=="__main__":
    main()
