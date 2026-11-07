#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V454: cross-platform, source-only, digest-checked CLS BBHost 0.2.26 overlay.

Linux first stages the exact published CLS YT 1.4.0 source against source-pinned
BBHost 0.2.26 and its original YT base. Package ONLY the 22 changed/new BBHost
source files and 6 YT files. Windows receives those exact bytes, avoiding
Git-for-Windows CRLF patch differences; it never receives PS4 game assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

from stage_cls_yt_bbhost_v451 import CHANGED as HOST_CHANGED, NEW as HOST_NEW
from stage_cls_yt_source_v452 import CHANGED as YT_CHANGED, YT_COMMIT, PATCH_SHA
from compare_cls_bbhost_rebase_v450 import MODERN, EXPECTED_ZIP

FILES = {
    **{"host/"+p: p for p in HOST_CHANGED + HOST_NEW},
    **{"yt/"+p: p for p in YT_CHANGED},
}
MAX_ITEM = 1_500_000
MAX_BUNDLE = 12_000_000
SCHEMA = "SHYT_V454_REAL_YT140_BBHOST026_VERIFIED_SOURCE_OVERLAY_V1"

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def commit(root:Path)->str:
    p=subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],
                     text=True,capture_output=True,timeout=12)
    if p.returncode:
        raise ValueError("missing pinned Git source checkout")
    return p.stdout.strip()

def assert_pins(host:Path,yt:Path)->None:
    if commit(host)!=MODERN or commit(yt)!=YT_COMMIT:
        raise ValueError("original host/YT commit differs from verified source")
    if not (host/"cmake/bbsc_yt.cmake").exists():
        # Linux packaging only has the new source; Windows must have it after writing.
        return

def bundle(host:Path,yt:Path,dest:Path)->dict:
    assert_pins(host,yt)
    if dest.exists() or dest.is_symlink():
        raise ValueError("source-only artifact output already exists")
    if len(FILES)!=len(HOST_CHANGED)+len(HOST_NEW)+len(YT_CHANGED):
        raise ValueError("unexpected duplicate source path")
    results:dict[str,dict]={}
    payload:dict[str,bytes]={}
    size=0
    for key,rel in sorted(FILES.items()):
        root=host if key.startswith("host/") else yt
        p=root/rel
        if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_ITEM:
            raise ValueError("source file missing or exceeds safety bounds: "+key)
        contents=p.read_bytes()
        size+=len(contents)
        if size>MAX_BUNDLE or b"\x00" in contents:
            raise ValueError("binary or oversized source bundle")
        results[key]={"size":len(contents),"sha256":sha(contents)}
        payload[key]=contents
    if b"bbcoop_install(" not in payload["host/src/yt/yt_host.cpp"]:
        raise ValueError("game hooking integration missing")
    if b"BB_ONLINE_UNLOCKED_FPS" not in payload["host/src/engine/frame_rate.cpp"]:
        raise ValueError("real original online frame policy missing")
    if b"hle_thread_enter_guest" not in payload["yt/emulator/src/core/bloodborne_patches.cpp"]:
        raise ValueError("real original guest game-link thread fix missing")
    manifest={"schema":SCHEMA,"source_release_sha256":EXPECTED_ZIP,
              "original_yt_patch_sha256":PATCH_SHA,
              "bbhost_source_sha":MODERN,"yt_source_sha":YT_COMMIT,
              "file_sha256":results,
              "proof_only":"source bytes + patches, not compiled/running game"}
    with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr("manifest.json",json.dumps(manifest,sort_keys=True,indent=2)+"\n")
        for key,content in payload.items():
            z.writestr(key,content)
    return {"mode":"package","files":len(payload),"expanded_source_bytes":size,
            "artifact_sha256":sha(dest.read_bytes()),"host_files":len(HOST_CHANGED)+len(HOST_NEW),
            "yt_files":len(YT_CHANGED),"no_proprietary_data":True}

def stage(host:Path,yt:Path,artifact:Path)->dict:
    assert_pins(host,yt)
    if not artifact.is_file() or artifact.is_symlink() or artifact.stat().st_size>MAX_BUNDLE:
        raise ValueError("unexpected source-only artifact")
    with zipfile.ZipFile(artifact) as z:
        members=z.namelist()
        expected={"manifest.json"}|set(FILES)
        if set(members)!=expected or len(members)!=len(expected):
            raise ValueError("archive path set is not exact allowlist")
        for n in members:
            p=PurePosixPath(n)
            if p.is_absolute() or ".." in p.parts or "\\" in n:
                raise ValueError("unsafe source path")
        meta=json.loads(z.read("manifest.json"))
        if (meta.get("schema")!=SCHEMA or meta.get("source_release_sha256")!=EXPECTED_ZIP or
            meta.get("original_yt_patch_sha256")!=PATCH_SHA or
            meta.get("bbhost_source_sha")!=MODERN or meta.get("yt_source_sha")!=YT_COMMIT or
            set(meta.get("file_sha256",{}))!=set(FILES)):
            raise ValueError("source bundle provenance drift")
        for key,rel in sorted(FILES.items()):
            info=z.getinfo(key)
            if info.file_size>MAX_ITEM or info.file_size==0:
                raise ValueError("source bundle item too large or empty")
            data=z.read(info)
            expected_file=meta["file_sha256"][key]
            if sha(data)!=expected_file["sha256"] or len(data)!=expected_file["size"]:
                raise ValueError("source file mismatch: "+key)
            root=host if key.startswith("host/") else yt
            path=root/rel
            if path.is_symlink() or (key in ("host/"+p for p in HOST_NEW) and path.exists()):
                raise ValueError("new source path conflict: "+key)
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
    if "include(cmake/bbsc_yt.cmake)" not in (host/"CMakeLists.txt").read_text(encoding="utf-8"):
        raise ValueError("host CMake integration not admitted")
    return {"mode":"stage","source_overlay_bytes_sha256":sha(artifact.read_bytes()),
            "host_files":len(HOST_CHANGED)+len(HOST_NEW),"yt_files":len(YT_CHANGED),
            "proof_only":"original source overlay admitted, not Windows game boot"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("package","stage"),required=True)
    p.add_argument("--host",type=Path,required=True)
    p.add_argument("--yt",type=Path,required=True)
    p.add_argument("--bundle",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    result=bundle(a.host,a.yt,a.bundle) if a.mode=="package" else stage(a.host,a.yt,a.bundle)
    a.report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("SHYT_V454_CROSS_OS_CLS_YT140_BBHOST026_VERIFIED_SOURCE_"+a.mode.upper()+"_PASS")
    print("SHYT_V454_APPROVED_SOURCE_FILES",len(FILES),"NO_GAME_FILES_NO_LIVE_DEPLOYMENT")

if __name__=="__main__":
    main()
