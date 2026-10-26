#!/usr/bin/env python3
"""V111: bound real Windows C++ Ninja jobs to avoid multi-gigabyte compiler thrash.

The pinned original game's MSYS2 build.sh is patched AFTER V103+V106.
This is a conservative, source-exact change to concurrency, not gameplay or
the bbnet/GPU target list. The hosted runner has limited CPU and memory.
"""
from __future__ import annotations

import argparse
from pathlib import Path

RELATIVE = "bbport/build.sh"
MARKER = "SHYT-V111-NINJA-BOUNDED-COMPILE"
BBNET = "    if ! ninja -C out/gpu bbnet > out/bbnet-build.log 2>&1"
GPU = "    if ! ninja -C out/gpu bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1"
PREFIX = 'ninja -j "${SHYT_NATIVE_NINJA_JOBS:-2}" -C out/gpu '


def transform(text: str) -> str:
    if MARKER in text:
        raise ValueError("V111 Ninja CPU guard already applied")
    if (text.count(BBNET) != 1 or text.count(GPU) != 1
        or "SHYT-V103-NATIVE-BBNET-FIRST" not in text
        or "SHYT-V106-BBNET-ONLY" not in text
        or "MINGW*|MSYS*)" not in text):
        raise ValueError("V111 unexpected pinned Windows native Ninja source")
    return text.replace(
        BBNET,
        "    # " + MARKER + ": at most two heavy C++ units at once by default.\n"
        "    if ! " + PREFIX + "bbnet > out/bbnet-build.log 2>&1", 1
    ).replace(
        GPU,
        "    if ! " + PREFIX + "bb-probe bb-gpu-capabilities bb-play > out/gpu-build.log 2>&1", 1
    )


def stage(root: Path) -> None:
    file = root / RELATIVE
    if not file.is_file() or file.is_symlink():
        raise ValueError("V111 original Windows build.sh missing or symlinked")
    patched = transform(file.read_text(encoding="utf-8"))
    file.write_text(patched, encoding="utf-8")
    print("SHYT_V111_NATIVE_NINJA_COMPILER_CONCURRENCY_TWO_STAGED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pinned_checkout", type=Path)
    stage(parser.parse_args().pinned_checkout)
