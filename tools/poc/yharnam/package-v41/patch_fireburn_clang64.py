#!/usr/bin/env python3
"""Pinned FireBurn FSR-Vulkan Windows CLANG64 wide-printf portability fix.

FireBurn/FSR-Vulkan submodule c64f093404125e960813f95f1996c14780f0dd69,
AMD FidelityFX SDK ffx-1.1.4/src/shared/ffx_message.cpp. The MSVC-only
swprintf_s(buffer, 512, format, message) is absent in MSYS2 Clang64 C++.
Use the C++17 std::swprintf(buffer, capacity, format, message) with its same
bounded 512-wide-char buffer. Apply ONLY to a freshly checked out copy, not
to the vendor repository. Refuse unknown source revisions and second apply.
"""
from __future__ import annotations
import argparse
from pathlib import Path

SUBMODULE = "c64f093404125e960813f95f1996c14780f0dd69"
TARGET = "bbport/gpu/third_party/fsr-vulkan/upstream/ffx-1.1.4/sdk/src/shared/ffx_message.cpp"
HEADERS = '#include <windows.h>  // required for OutputDebugString()\n'
HEADER_PATCH = HEADERS + '#include <cwchar>  // C++17 bounded std::swprintf for CLANG64\n'
ERROR = 'swprintf_s(buffer, 512, L"FSR_API_DEBUG_ERROR: %ls\\n", message);'
WARNING = 'swprintf_s(buffer, 512, L"FSR_API_DEBUG_WARNING: %ls\\n", message);'


def transform(source: str) -> str:
    if "std::swprintf" in source or "#include <cwchar>  // C++17 bounded" in source:
        raise ValueError("FSR source already patched")
    for required in (HEADERS, ERROR, WARNING, "wchar_t buffer[512];",
                     "OutputDebugStringW(buffer);", "FidelityFX SDK"):
        if source.count(required) != 1:
            raise ValueError("Pinned FireBurn FSR C++ source drifted: " + required[:55])
    if source.count("swprintf_s(") != 2:
        raise ValueError("unexpected additional swprintf_s calls")
    source = source.replace(HEADERS, HEADER_PATCH, 1)
    source = source.replace(ERROR, ERROR.replace("swprintf_s(", "std::swprintf("), 1)
    source = source.replace(WARNING, WARNING.replace("swprintf_s(", "std::swprintf("), 1)
    return source


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pinned_checkout", type=Path)
    args = p.parse_args()
    target = args.pinned_checkout / TARGET
    if not target.is_file():
        p.error("pinned FireBurn FSR C++ source missing")
    old = target.read_text("utf-8")
    new = transform(old)
    target.write_text(new, encoding="utf-8")
    print("SHYT_FSR_WINDOWS_CLANG64_CXX17_WPRINTF_PATCH_PASS")


if __name__ == "__main__":
    main()
