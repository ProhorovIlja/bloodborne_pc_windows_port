#!/usr/bin/env python3
"""Source-locked Windows CLANG64 compatibility for pinned AMD FSR 1.1.4 Vulkan TU.

Original FireBurn/FSR-Vulkan c64f0934, git blob b2439b6. MSYS2 clang 17
doesn't get placement operator new or the unqualified log2 transitively.
Explicit C++ standard headers and std:: qualified functions preserve behavior,
upscaler and Vulkan backend; no compiler flags relaxed or features removed.
CI's disposable checked-out submodule only. Fail closed on any source drift.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

RELATIVE = ("bbport/gpu/third_party/fsr-vulkan/"
            "upstream/ffx-1.1.4/sdk/src/backends/vk/ffx_vk.cpp")
SUBMODULE_COMMIT = "c64f093404125e960813f95f1996c14780f0dd69"
ORIGINAL_BLOB = "b2439b6bb8c32196c4ba88c0aa61fd4d8333c200"
HEADER = "#include <FidelityFX/host/ffx_interface.h>\n"
LOG2 = "floor(log2(FFX_MAXIMUM("
FIXED_LOG2 = "std::floor(std::log2(FFX_MAXIMUM("
INCLUDES = "#include <cmath>\n#include <new>\n"

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def patch_text(source: str) -> str:
    if any(marker in source for marker in (FIXED_LOG2, "#include <new>", "#include <cmath>")):
        raise ValueError("Pinned AMD FSR Vulkan fix already applied or different source")
    for anchor in (HEADER, LOG2,
                   "new (&backendContext->uniformBufferMutex) std::mutex();",
                   "Copyright (C) 2024 Advanced Micro Devices, Inc."):
        n = source.count(anchor)
        if n != 1:
            raise ValueError(f"Pinned AMD FSR vk source anchor drift: {anchor!r} found {n}")
    return source.replace(HEADER, INCLUDES + HEADER, 1).replace(LOG2, FIXED_LOG2, 1)

def patch_file(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError("Pinned FSR Vulkan source must be a regular file")
    before = path.read_bytes()
    normalized = before.replace(b"\r\n", b"\n")
    if git_blob(normalized) != ORIGINAL_BLOB:
        raise ValueError("Pinned FSR Vulkan git blob mismatch: " + git_blob(normalized))
    updated = patch_text(normalized.decode("utf-8")).encode("utf-8")
    path.write_bytes(updated)
    print("SHYT_PINNED_FSR_VK_CLANG64_HEADERS_AND_STD_MATH_FIX_PASS " + git_blob(updated))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    opts = parser.parse_args()
    patch_file(opts.upstream / RELATIVE)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
