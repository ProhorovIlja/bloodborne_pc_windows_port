#!/usr/bin/env python3
"""V116: reduce hosted Windows Clang64 CI debug-info cost, not optimizations.

The original native port remains unchanged: only the pinned internal CI
checkout receives this transform AFTER the ccache injection and V115.
Use line-table DWARF rather than full -g for large Release-with-debug
C++ builds while retaining exactly -O2 and -DNDEBUG.
"""
from __future__ import annotations

import argparse
from pathlib import Path

TARGET = "bbport/build.sh"
MARKER = "SHYT-V116-NATIVE-LEAN-DWARF"
ANCHOR = (
    "-DCMAKE_CXX_COMPILER_LAUNCHER=ccache "
    "> out/cmake-configure.log 2>&1; then"
)
NEW = r"""-DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
        -DCMAKE_C_FLAGS_RELWITHDEBINFO="-O2 -gline-tables-only -DNDEBUG" \
        -DCMAKE_CXX_FLAGS_RELWITHDEBINFO="-O2 -gline-tables-only -DNDEBUG" \
        -DCMAKE_SUPPRESS_REGENERATION=ON > out/cmake-configure.log 2>&1; then"""


def transform(source: str) -> str:
    if MARKER in source:
        raise ValueError("V116 internal native Clang64 low-debug guard already applied")
    if (
        source.count(ANCHOR) != 1
        or "SHYT-V115-NATIVE-CMAKE-CONFIGURE-LOG" not in source
        or "SHYT-V111-NINJA-BOUNDED-COMPILE" not in source
        or "MINGW*|MSYS*)" not in source
        or "CMAKE_BUILD_TYPE=RelWithDebInfo" not in source
    ):
        raise ValueError("V116 pinned original Windows Clang64 CMake script drifted")
    source = source.replace(
        "    # SHYT-V115-NATIVE-CMAKE-CONFIGURE-LOG:",
        f"    # {MARKER}: Clang64 internal CI line tables only, still -O2.\n"
        "    # SHYT-V115-NATIVE-CMAKE-CONFIGURE-LOG:",
        1,
    )
    return source.replace(ANCHOR, NEW, 1)


def stage(root: Path) -> None:
    dest = root / TARGET
    if not dest.is_file() or dest.is_symlink():
        raise ValueError("V116 original Windows build script unavailable or symlinked")
    dest.write_text(transform(dest.read_text(encoding="utf-8")), encoding="utf-8")
    print("SHYT_V116_INTERNAL_CLANG64_LEAN_DWARF_STAGED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pinned_checkout", type=Path)
    stage(parser.parse_args().pinned_checkout)
