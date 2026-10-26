#!/usr/bin/env python3
"""V100: exact-source Sirit C++20 std::abort declaration for Windows CLANG64.

Original pinned Yharnam Together 77e3507 Sirit src/stream.h uses
std::abort() yet does not include <cstdlib>. Actual Windows full-native
CI timed out after repeatedly failing compilation with -Werror.
This is a minimal portable, standard-header-only backport.
"""
from __future__ import annotations
import argparse
from pathlib import Path

TARGET = "bbport/gpu/third_party/sirit/src/stream.h"
ANCHOR = "#include <cstddef>\n"
PATCHED = ANCHOR + "#include <cstdlib>  // V100: std::abort requires the C++ standard declaration\n"
CALL = "            std::abort();\n"
MARKER = "V100: std::abort requires the C++ standard declaration"

def patch_header(original: str) -> str:
    if MARKER in original or "#include <cstdlib>" in original:
        raise ValueError("V100 pinned Sirit source already includes cstdlib")
    if original.count(ANCHOR) != 1 or original.count(CALL) != 1:
        raise ValueError("V100 pinned Sirit source drift at cstddef/std::abort")
    if "#include <bit>\n" not in original or "namespace Sirit {" not in original:
        raise ValueError("V100 unknown Sirit layout")
    return original.replace(ANCHOR, PATCHED, 1)

def stage(checkout: Path) -> None:
    dest = checkout / TARGET
    if not dest.is_file():
        raise ValueError("V100 actual pinned Sirit stream.h missing")
    original = dest.read_text(encoding="utf-8")
    fixed = patch_header(original)
    dest.write_text(fixed,encoding="utf-8")
    print("SHYT_V100_PINNED_SIRIT_CSTDLIB_STANDARD_HEADER_PATCH_PASS")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pinned_checkout",type=Path)
    stage(parser.parse_args().pinned_checkout)
