#!/usr/bin/env python3
"""One exact-blob fix for pinned AMD FidelityFX FSR SDK Win32 CLANG64.

The pinned FireBurn/FSR-Vulkan submodule c64f093 contains MSVC-only
swprintf_s(buffer, size, format, message) calls in ffx_message.cpp.
MSYS2 CLANG64 with MinGW C++17 exposes std::swprintf (same bounded
4-argument semantics) but not Microsoft's swprintf_s name. Preserve
the 512-wchar destination, arguments, diagnostic messages and license.

Never patch arbitrary source or silently apply twice. Worktree change
is confined to disposable CI's pinned Git submodule, not user's files.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

RELATIVE = (
    "bbport/gpu/third_party/fsr-vulkan/"
    "upstream/ffx-1.1.4/sdk/src/shared/ffx_message.cpp"
)
SUBMODULE_COMMIT = "c64f093404125e960813f95f1996c14780f0dd69"
ORIGINAL_BLOB = "e325a0553ef0ca48d3d42c60097e0f0cef154d46"


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") +
                        b"\0" + raw).hexdigest()


def one(text: str, before: str, after: str) -> str:
    occurrences = text.count(before)
    if occurrences != 1:
        raise ValueError(
            "Pinned FSR Windows CLANG64 source drift: "
            f"expected one occurrence of {before!r}, got {occurrences}")
    return text.replace(before, after, 1)


def patch_text(text: str) -> str:
    if "std::swprintf(" in text or "#include <cwchar>" in text:
        raise ValueError("FSR Windows CLANG64 compatibility fix already applied")
    for required in (
        "Copyright (C) 2025 Advanced Micro Devices, Inc.",
        "#include <FidelityFX/host/ffx_message.h>",
        "OutputDebugStringW(buffer);",
        "wchar_t buffer[512];",
    ):
        if required not in text:
            raise ValueError("Pinned FSR source marker missing: " + required)
    text = one(
        text,
        "#include <FidelityFX/host/ffx_message.h>\n",
        "#include <cwchar>  // std::swprintf is portable to MinGW CLANG64\n"
        "#include <FidelityFX/host/ffx_message.h>\n",
    )
    text = one(
        text,
        'swprintf_s(buffer, 512, L"FSR_API_DEBUG_ERROR: %ls\\n", message);',
        'std::swprintf(buffer, 512, L"FSR_API_DEBUG_ERROR: %ls\\n", message);',
    )
    text = one(
        text,
        'swprintf_s(buffer, 512, L"FSR_API_DEBUG_WARNING: %ls\\n", message);',
        'std::swprintf(buffer, 512, L"FSR_API_DEBUG_WARNING: %ls\\n", message);',
    )
    return text


def patch_file(path: Path) -> None:
    original = path.read_bytes()
    actual_blob = git_blob(original)
    if actual_blob != ORIGINAL_BLOB:
        # Windows Git may check out *this pinned text file* with CRLF.
        # Normalizing CRLF to LF must reproduce the IDENTICAL Git blob;
        # otherwise refuse, never treat arbitrary changed FSR as safe.
        canonical = original.replace(b"\r\n", b"\n")
        if b"\r\n" not in original or git_blob(canonical) != ORIGINAL_BLOB:
            raise ValueError(
                f"FSR version mismatch: required {ORIGINAL_BLOB}, "
                f"got {actual_blob} (CRLF-normalized={git_blob(canonical)})")
        original = canonical
    updated = patch_text(original.decode("utf-8"))
    path.write_bytes(updated.encode("utf-8"))
    print("SHYT_FSR_PINNED_MINGW_WPRINTF_FIXED:" + git_blob(
        updated.encode("utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, required=True)
    args = parser.parse_args()
    path = args.upstream / RELATIVE
    patch_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
