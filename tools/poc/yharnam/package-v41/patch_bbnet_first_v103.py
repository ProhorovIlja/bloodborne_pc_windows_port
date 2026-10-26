#!/usr/bin/env python3
"""V103: compile the true native game's bbnet library before GPU shaders.

Source-pinned original bbport/build.sh Windows CLANG64 branch uses CMake
with Ninja but previously built all GPU/renderer targets together. bbnet
includes V97/V98/V99 co-op and native shadNet wire. A failing native
gameplay .cpp should stop early and preserve bbnet-build.log instead of
expending time compiling the full graphics library first.
"""
from __future__ import annotations
import argparse
from pathlib import Path

SOURCE="bbport/build.sh"
OLD='''    echo "GPU library and loader: LTO ${BB_LTO:-OFF}"
    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then'''
NEW='''    echo "GPU library and loader: LTO ${BB_LTO:-OFF}"
    # SHYT-V103-NATIVE-BBNET-FIRST: explicitly build actual co-op game
    # and native network C++ before the large GPU/FSR compile and link.
    if ! ninja -C out/gpu bbnet > out/bbnet-build.log 2>&1; then
        grep -v '^\\[' out/bbnet-build.log | tail -100 >&2
        echo 'Native game bbnet failed (full log: out/bbnet-build.log)' >&2
        exit 1
    fi
    echo 'SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED'
    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then'''
MARKER="SHYT-V103-NATIVE-BBNET-FIRST"

def transform(code:str)->str:
    if MARKER in code:
        raise ValueError("V103 native gameplay preflight already applied")
    if code.count(OLD)!=1 or "case $(uname -s) in" not in code or "MINGW*|MSYS*)" not in code:
        raise ValueError("V103 unexpected pinned original Windows build.sh")
    if 'target name' in code:
        raise ValueError("V103 unexpected unreviewed build marker")
    return code.replace(OLD,NEW,1)

def stage(root:Path)->None:
    target=root/SOURCE
    if not target.is_file() or target.is_symlink():
        raise ValueError("V103 original pinned Windows build shell missing or symlink")
    code=target.read_text(encoding="utf-8")
    patched=transform(code)
    cmake=(root/"bbport/gpu/CMakeLists.txt").read_text(encoding="utf-8")
    if "add_library(bbnet STATIC" not in cmake or "target_link_libraries(bbgpu PUBLIC bbnet)" not in cmake:
        raise ValueError("V103 native game bbnet not a CMake target/dependency")
    target.write_text(patched,encoding="utf-8")
    print("SHYT_V103_TRUE_NATIVE_GAME_BBNET_FIRST_STAGED")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("original_upstream",type=Path)
    stage(parser.parse_args().original_upstream)
