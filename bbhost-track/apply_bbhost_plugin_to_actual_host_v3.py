#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V3: build the actual official BBHost executable WITH the Seamless Hunt
read-only plugin and V2 STUN source patch, not a synthetic substitute.

Only a disposable SHA-pinned upstream checkout can be patched. All game
files remain private outside GitHub. This is a BBHost game host, NOT
Yharnam Together game logic yet.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess

UPSTREAM="b0098e04b889e2e70b4af84be1ce809d7af3ff95"
CMAKE_BLOB="672a3c1c3b9264cf3cc34d4606b844e5cba87717"
CMAKE_ANCHOR="""set_target_properties(bb_plugin_hello PROPERTIES OUTPUT_NAME hello PREFIX ""
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/plugins)"""
CMAKE_APPEND="""
# SHYT V3: build an opt-in, source-only real BBHost plugin beside hello.
# It performs no network injection or game writes and cannot load into
# a host that doesn't expose the exact verified plugin API.
add_library(bb_plugin_shyt MODULE plugins/shyt_probe/shyt_bbhost_probe_v1.c)
target_include_directories(bb_plugin_shyt PRIVATE include)
set_target_properties(bb_plugin_shyt PROPERTIES
  OUTPUT_NAME shyt_bbhost_probe PREFIX ""
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/plugins)
"""

def git(root:Path,*args:str)->str:
    result=subprocess.run(["git","-C",str(root),*args],
        capture_output=True,text=True,timeout=12)
    if result.returncode:raise ValueError("unverified BBHost checkout")
    return result.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    a=p.parse_args()
    root=a.upstream_checkout.resolve(strict=True)
    if git(root,"rev-parse","HEAD")!=UPSTREAM:
        raise ValueError("unverified BBHost release")
    cmake=root/"CMakeLists.txt"
    plugin_root=root/"plugins/shyt_probe"
    plugin=plugin_root/"shyt_bbhost_probe_v1.c"
    source=Path(__file__).resolve().parent/"shyt_bbhost_probe_v1.c"
    world_header=Path(__file__).resolve().parent/"yt_world_event_ledger_v4.h"
    if (cmake.is_symlink() or not cmake.is_file() or
        git(root,"rev-parse","HEAD:CMakeLists.txt")!=CMAKE_BLOB or
        git(root,"hash-object","CMakeLists.txt")!=CMAKE_BLOB or
        not source.is_file() or source.is_symlink() or
        not world_header.is_file() or world_header.is_symlink() or
        plugin_root.exists() or plugin_root.is_symlink()):
        raise ValueError("CMake or plugin input not clean and source pinned")
    original=cmake.read_text(encoding="utf-8")
    if original.count(CMAKE_ANCHOR)!=1:
        raise ValueError("original BBHost CMake plugin insertion drift")
    if a.mode=="apply":
        plugin_root.mkdir()
        shutil.copyfile(source,plugin)
        shutil.copyfile(world_header,plugin_root/world_header.name)
        cmake.write_text(original.replace(CMAKE_ANCHOR,
            CMAKE_ANCHOR+CMAKE_APPEND),encoding="utf-8")
    print("SHYT_BBHOST_V3_REAL_HOST_PLUGIN_CMAKE_"+("APPLIED" if a.mode=="apply" else "PINNED"))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,subprocess.TimeoutExpired):
        raise SystemExit("SHYT_BBHOST_V3_REFUSED_UNVERIFIED_HOST_SOURCE") from None
