#!/usr/bin/env python3
"""Exact original Sirit stream.h standard-header portability for Windows CLANG64.

Yharnam Together's native Bloodborne renderer vendors sirit. At pin
77e350743a7cb4524cfcc1782fb6e3af64e25b15 its stream.h calls
std::abort() without including <cstdlib>. MSYS2 libc++ will not get
std::abort from other unrelated headers. Fix this source only in the
disposable CI checkout. No shader behavior, optimizations or features change.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

RELATIVE = "bbport/gpu/third_party/sirit/src/stream.h"
ORIGINAL_BLOB = "31c2680c2f2c6977e5368e4a28262d8db611e3f8"
OLD = "#include <cassert>\n"
NEW = "#include <cassert>\n#include <cstdlib> // std::abort must be declared explicitly\n"

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def patch_source(text: str) -> str:
    if "std::abort();" not in text or "3-Clause BSD License" not in text:
        raise ValueError("Wrong Sirit stream.h source")
    if text.count(OLD) != 1 or "#include <cstdlib>" in text:
        raise ValueError("Sirit source drift / compatibility header already applied")
    return text.replace(OLD, NEW, 1)

def patch_file(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing pinned original sirit header")
    raw = path.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n")
    if git_blob(canonical) != ORIGINAL_BLOB:
        raise ValueError("Wrong original Sirit git blob: " + git_blob(canonical))
    updated = patch_source(canonical.decode("utf-8")).encode("utf-8")
    path.write_bytes(updated)
    print("SHYT_ORIGINAL_SIRIT_WINDOWS_CSTDLIB_FIX_PASS " + git_blob(updated))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    args = parser.parse_args()
    patch_file(args.upstream / RELATIVE)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
