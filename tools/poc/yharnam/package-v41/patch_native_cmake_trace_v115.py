#!/usr/bin/env python3
"""V115: retain original Clang64 CMake configure output from the real Windows port.

A prior real 165-minute CI timeout saved CMakeCache but no bbnet/GPU
build log; pinned bbport/build.sh deliberately redirected CMake to /dev/null.
Source-exact, Windows-only change. The CI deliberately injects ccache BEFORE
this transform. The ccache-aware CMake line must match as one complete stage.
No game functionality or release flags.
"""
from __future__ import annotations

import argparse
from pathlib import Path

TARGET = "bbport/build.sh"
MARKER = "SHYT-V115-NATIVE-CMAKE-CONFIGURE-LOG"
ORIGINAL = """    cmake -S gpu -B out/gpu -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBB_PGO=off \\
        -DBB_LTO="${BB_LTO:-OFF}" -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache >/dev/null
    echo "GPU library and loader: LTO ${BB_LTO:-OFF}" """
# The true original line ends at the quote, not after a trailing space.
ORIGINAL = ORIGINAL.rstrip()
PATCHED = """    # SHYT-V115-NATIVE-CMAKE-CONFIGURE-LOG: preserve configure output
    # for stalled jobs; stdout was previously sent to /dev/null.
    mkdir -p out
    echo SHYT_V115_NATIVE_CMAKE_CONFIGURE_START
    if ! cmake -S gpu -B out/gpu -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBB_PGO=off \\
        -DBB_LTO="${BB_LTO:-OFF}" -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache > out/cmake-configure.log 2>&1; then
        echo SHYT_V115_NATIVE_CMAKE_CONFIGURE_FAILED >&2
        tail -n 100 out/cmake-configure.log >&2 || true
        exit 1
    fi
    echo SHYT_V115_NATIVE_CMAKE_CONFIGURE_PASS
    echo "GPU library and loader: LTO ${BB_LTO:-OFF}" """ 
PATCHED = PATCHED.rstrip()


def transform(original: str) -> str:
    if MARKER in original:
        raise ValueError("V115 Windows CMake trace already added")
    if original.count(ORIGINAL) != 1 or "MINGW*|MSYS*)" not in original:
        raise ValueError("V115 original Windows CMake configure source changed")
    if "SHYT-V103-NATIVE-BBNET-FIRST" not in original or "SHYT-V111-NINJA-BOUNDED-COMPILE" not in original:
        raise ValueError("V115 missing native Windows game build pin guards")
    return original.replace(ORIGINAL, PATCHED, 1)


def stage(root: Path) -> None:
    dest = root / TARGET
    if not dest.is_file() or dest.is_symlink():
        raise ValueError("V115 pinned original bbport build script missing or symlinked")
    changed = transform(dest.read_text(encoding="utf-8"))
    dest.write_text(changed, encoding="utf-8")
    print("SHYT_V115_PINNED_WINDOWS_NATIVE_CMAKE_CONFIGURE_EVIDENCE_STAGED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("pinned_upstream", type=Path)
    stage(p.parse_args().pinned_upstream)
