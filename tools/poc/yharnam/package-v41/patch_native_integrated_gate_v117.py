#!/usr/bin/env python3
"""Verify authentic Yharnam Together bbnet BEFORE building the full native GPU.

CI-only fail-closed transform over the V103/V106/V111/V115/V116 pinned
original Windows builder; never changes gameplay or network protocols.
"""
from __future__ import annotations
import argparse
from pathlib import Path

TARGET = "bbport/build.sh"
MARKER = "SHYT-V117-VERIFY-ACTUAL-BBNET-BEFORE-GPU"
ANCHOR = """    echo 'SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED'
    # SHYT-V106-BBNET-ONLY:"""
INSERT = r"""    echo 'SHYT_V103_REAL_GAME_CXX_BBNET_COMPILED'
    # SHYT-V117-VERIFY-ACTUAL-BBNET-BEFORE-GPU: native provenance guard.
    if [[ "%FLAG%" == 1 ]]; then
        python ../../tools/poc/yharnam/package-v41/verify_bbnet_archive_v108.py \
            out/gpu/libbbnet.a out/shyt-v101-gameplay-source.json .. || {
            echo 'SHYT_V117_REAL_NATIVE_BBNET_PROVENANCE_FAILURE' >&2
            exit 1
        }
        echo SHYT_V117_ORIGINAL_GAME_CXX_ARCHIVE_VERIFIED_BEFORE_GPU
    fi
    # SHYT-V106-BBNET-ONLY:""".replace("%FLAG%", "$" + "{SHYT_V117_VERIFY_AFTER_BBNET:-0}")


def transform(source: str) -> str:
    if MARKER in source:
        raise ValueError("V117 already integrated")
    required = (
        "SHYT-V103-NATIVE-BBNET-FIRST",
        "SHYT-V106-BBNET-ONLY",
        "SHYT-V111-NINJA-BOUNDED-COMPILE",
        "SHYT-V115-NATIVE-CMAKE-CONFIGURE-LOG",
        "SHYT-V116-NATIVE-LEAN-DWARF",
        "MINGW*|MSYS*)",
    )
    if source.count(ANCHOR) != 1 or not all(x in source for x in required):
        raise ValueError("V117 original pinned game build source differs")
    if source.index(ANCHOR) > source.index("bb-probe bb-gpu-capabilities bb-play"):
        raise ValueError("V117 gameplay bbnet did not precede GPU")
    return source.replace(ANCHOR, INSERT, 1)


def stage(checkout: Path) -> None:
    target = checkout / TARGET
    if not target.is_file() or target.is_symlink():
        raise ValueError("V117 original Windows builder missing or symlinked")
    target.write_text(transform(target.read_text(encoding="utf-8")), encoding="utf-8")
    print("SHYT_V117_SINGLE_NATIVE_GAME_BUILD_PROVENANCE_STAGED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pinned_checkout", type=Path)
    stage(parser.parse_args().pinned_checkout)
