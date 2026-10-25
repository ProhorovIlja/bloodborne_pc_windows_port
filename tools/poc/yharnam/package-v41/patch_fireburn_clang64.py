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
FRAME_TARGET = "bbport/gpu/third_party/fsr-vulkan/upstream/ffx-1.1.4/sdk/src/components/frameinterpolation/ffx_frameinterpolation.cpp"
FRAME_HEADER = "#include <algorithm>    // for max used inside SPD CPU code.\n"
FRAME_ADDED_HEADER = FRAME_HEADER + "#include <iterator>   // portable C++17 std::size for fixed arrays\n"
FRAME_COUNT = 14  # exact number of pinned AMD SDK _countof(array) occurrences
OPTICAL_TARGET = "bbport/gpu/third_party/fsr-vulkan/upstream/ffx-1.1.4/sdk/src/components/opticalflow/ffx_opticalflow.cpp"
OPTICAL_COUNT = 9  # three each of srv/uav/cbBindingNames arrays
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


def transform_frame_interpolation(source: str) -> str:
    """Convert pinned MSVC-only _countof(array) into C++17 std::size(array).

    All 14 occurrences in this pinned source refer to fixed-size C++ arrays,
    including local copyJobs. Fail closed if the AMD vendored file drifts.
    """
    if "std::size(" in source or "portable C++17 std::size for fixed arrays" in source:
        raise ValueError("frame interpolation source already patched")
    if source.count(FRAME_HEADER) != 1:
        raise ValueError("pinned FidelityFX frame interpolation header drifted")
    if source.count("_countof(") != FRAME_COUNT:
        raise ValueError("pinned FidelityFX frame interpolation _countof calls drifted")
    # No macro definitions or pointer calls are supported by this patch.
    return source.replace(FRAME_HEADER, FRAME_ADDED_HEADER, 1).replace(
        "_countof(", "std::size("
    )


def transform_opticalflow(source: str) -> str:
    """Windows CLANG64: replace 9 MSVC-only array counts in optical flow.

    The original fixed Binding arrays are not pointers. Validate exact
    pinned call sites and headers, fail closed on unseen SDK layout.
    """
    if "std::size(" in source or "portable C++17 std::size for fixed arrays" in source:
        raise ValueError("opticalflow already patched")
    if source.count(FRAME_HEADER) != 1 or source.count("_countof(") != OPTICAL_COUNT:
        raise ValueError("pinned FidelityFX opticalflow source drifted")
    for name in ("srvBindingNames", "uavBindingNames", "cbBindingNames"):
        if source.count(f"_countof({name})") != 3 or source.count(f"static const Binding {name}[]") != 1:
            raise ValueError("pinned FidelityFX opticalflow binding array drifted: " + name)
    return source.replace(FRAME_HEADER, FRAME_ADDED_HEADER, 1).replace(
        "_countof(", "std::size("
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pinned_checkout", type=Path)
    args = p.parse_args()
    target = args.pinned_checkout / TARGET
    frame_target = args.pinned_checkout / FRAME_TARGET
    optical_target = args.pinned_checkout / OPTICAL_TARGET
    if not target.is_file() or not frame_target.is_file() or not optical_target.is_file():
        p.error("pinned FireBurn FSR C++ source missing")
    old = target.read_text("utf-8")
    frame_old = frame_target.read_text("utf-8")
    optical_old = optical_target.read_text("utf-8")
    # Strictly validate ALL THREE files before modifying the checked-out vendor subtree.
    new = transform(old)
    frame_new = transform_frame_interpolation(frame_old)
    optical_new = transform_opticalflow(optical_old)
    target.write_text(new, encoding="utf-8")
    frame_target.write_text(frame_new, encoding="utf-8")
    optical_target.write_text(optical_new, encoding="utf-8")
    print("SHYT_FSR_WINDOWS_CLANG64_THREE_HOST_CPP_PATCH_PASS")


if __name__ == "__main__":
    main()
