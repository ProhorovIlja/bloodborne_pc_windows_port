#!/usr/bin/env python3
"""V106: strictly opt-in native Windows CMake bbnet-only compile.

Builds the genuine original gameplay/network static library in the normal
pinned Clang64 environment. NEVER substitutes a mock or claims playable
game. Ordinary full builds remain unchanged.
"""
from __future__ import annotations
import argparse
from pathlib import Path

TARGET = "bbport/build.sh"
ANCHOR = """    echo 'SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED'
    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then"""
REPLACEMENT = """    echo 'SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED'
    # SHYT-V106-BBNET-ONLY: opt in for an authentic game-C++ library
    # compile, not a GPU renderer, launcher, archive or public release.
    if [[ ${SHYT_BBNET_ONLY:-0} == 1 ]]; then
        test -s out/gpu/libbbnet.a || {
            echo 'V106 original native bbnet archive missing' >&2
            exit 1
        }
        echo 'SHYT_V106_REAL_NATIVE_BBNET_ONLY_COMPILED'
        exit 0
    fi
    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1; then"""
MARKER = "SHYT-V106-BBNET-ONLY"

def transform(original: str) -> str:
    if MARKER in original:
        raise ValueError("V106 bbnet-only already added")
    if original.count(ANCHOR) != 1:
        raise ValueError(f"V106 pinned original Windows bbnet builder drift: {original.count(ANCHOR)}")
    if not all(x in original for x in (
        "SHYT-V103-NATIVE-BBNET-FIRST", "MINGW*|MSYS*)",
        "ninja -C out/gpu bbnet", "ninja -C out/gpu bb-probe")):
        raise ValueError("V106 not the source-reviewed original native Windows builder")
    return original.replace(ANCHOR, REPLACEMENT, 1)

def stage(root: Path) -> None:
    file = root/TARGET
    if not file.is_file() or file.is_symlink():
        raise ValueError("V106 actual original Windows builder missing or symlinked")
    src = file.read_text(encoding="utf-8")
    file.write_text(transform(src), encoding="utf-8")
    print("SHYT_V106_OPT_IN_REAL_NATIVE_GAME_BBNET_ONLY_STAGED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    stage(parser.parse_args().upstream)
