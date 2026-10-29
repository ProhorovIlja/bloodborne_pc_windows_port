#!/usr/bin/env python3
"""Source-locked AMD FidelityFX 1.1.4 SDK _countof migration for Windows CLANG64.

The original SDK host source assumes Microsoft's _countof extension, missing
from libc++/MinGW. Replace each verified array identifier with an equivalent
sizeof(array)/sizeof(array[0]) expression. No renderer feature/array changes.
Touches only pinned disposable CI FSR submodule, never the release game assets.
"""
from __future__ import annotations
import argparse
import hashlib
import re
from pathlib import Path

BASE = "bbport/gpu/third_party/fsr-vulkan/upstream/ffx-1.1.4/sdk/src/components"
SOURCE = {
    "opticalflow/ffx_opticalflow.cpp": ("ae94c2d04f6d6edc6766847c41e6f99254b2fdd9", 9),
    "frameinterpolation/ffx_frameinterpolation.cpp": ("b8f48c07933f5a444bc454dc9d9c68edaf461a3e", 14),
}
PIN = "c64f093404125e960813f95f1996c14780f0dd69"
COUNT = re.compile(r"(?<![\w])_countof\(([a-zA-Z_][a-zA-Z_0-9]*)\)")

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def patch_source(text: str, count: int) -> str:
    seen = COUNT.findall(text)
    if len(seen) != count or "_countof(" in COUNT.sub("", text):
        raise ValueError(f"Unreviewed AMD SDK _countof source: expected {count}, found {len(seen)}")
    if "Copyright (C) 2024 Advanced Micro Devices, Inc." not in text:
        raise ValueError("AMD SDK source copyright marker missing")
    output = COUNT.sub(lambda m: f"(sizeof({m.group(1)}) / sizeof(({m.group(1)})[0]))", text)
    if "_countof(" in output:
        raise ValueError("MSVC-only array length remains")
    return output

def patch_files(upstream: Path) -> None:
    staged = {}
    for rel, (expected_blob, count) in SOURCE.items():
        path = upstream / BASE / rel
        if not path.is_file() or path.is_symlink():
            raise ValueError("Pinned FidelityFX host component file missing")
        raw = path.read_bytes()
        canonical = raw.replace(b"\r\n", b"\n")
        if git_blob(canonical) != expected_blob:
            raise ValueError(f"AMD FidelityFX SDK git blob mismatch for {rel}")
        patched = patch_source(canonical.decode("utf-8"), count).encode("utf-8")
        staged[path] = patched
    # All-or-nothing validation before changing EITHER original source file.
    for path, raw in staged.items():
        path.write_bytes(raw)
        print(f"SHYT_PINNED_FSR_COUNT_OF_PASS {path.name} {git_blob(raw)}")

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    args = parser.parse_args()
    patch_files(args.upstream)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
