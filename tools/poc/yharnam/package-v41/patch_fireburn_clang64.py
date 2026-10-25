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
# V64: pinned FidelityFX Vulkan backend Windows CLANG64 compilation fix.
# It uses placement new and C math without declaring their standard headers.
VK_TARGET = "bbport/gpu/third_party/fsr-vulkan/upstream/ffx-1.1.4/sdk/src/backends/vk/ffx_vk.cpp"
VK_HEADER = "#include <vulkan/vulkan.h>\n"
VK_HEADER_PATCH = (VK_HEADER
    + "#include <new>    // placement new for Vk backend mutex, C++17\n"
    + "#include <cmath>  // std::floor, std::log2 for mip level count\n")
VK_PLACEMENT = "new (&backendContext->uniformBufferMutex) std::mutex();"
VK_MIP_EXPRESSION = "floor(log2(FFX_MAXIMUM("
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


def transform_vk_backend(source: str) -> str:
    """Pin-checked FidelityFX Vulkan backend C++17 portability only.

    The original Clang64 failure includes undeclared placement operator new
    and log2. Do not patch a different AMD SDK or apply twice.
    """
    if ("#include <new>    // placement new for Vk backend mutex" in source or
            "std::floor(std::log2(" in source):
        raise ValueError("pinned Vulkan backend source already patched")
    for required in (VK_HEADER, VK_PLACEMENT, VK_MIP_EXPRESSION,
                     "#include <FidelityFX/host/backends/vk/ffx_vk.h>"):
        if source.count(required) != 1:
            raise ValueError("pinned Vulkan backend source drifted: " + required)
    if source.count("log2(") != 1 or source.count("#include <new>") != 0:
        raise ValueError("pinned Vulkan backend math/new call sites drifted")
    source = source.replace(VK_HEADER, VK_HEADER_PATCH, 1)
    source = source.replace(VK_MIP_EXPRESSION,
                            "std::floor(std::log2(FFX_MAXIMUM(", 1)
    return source


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pinned_checkout", type=Path)
    args = p.parse_args()
    target = args.pinned_checkout / TARGET
    frame_target = args.pinned_checkout / FRAME_TARGET
    optical_target = args.pinned_checkout / OPTICAL_TARGET
    vk_target = args.pinned_checkout / VK_TARGET
    if (not target.is_file() or not frame_target.is_file() or
            not optical_target.is_file() or not vk_target.is_file()):
        p.error("pinned FireBurn FSR C++ source missing")
    old = target.read_text("utf-8")
    frame_old = frame_target.read_text("utf-8")
    optical_old = optical_target.read_text("utf-8")
    vk_old = vk_target.read_text("utf-8")
    # Validate ALL FOUR pinned AMD files before writing any replacement.
    new = transform(old)
    frame_new = transform_frame_interpolation(frame_old)
    optical_new = transform_opticalflow(optical_old)
    vk_new = transform_vk_backend(vk_old)
    target.write_text(new, encoding="utf-8")
    frame_target.write_text(frame_new, encoding="utf-8")
    optical_target.write_text(optical_new, encoding="utf-8")
    vk_target.write_text(vk_new, encoding="utf-8")
    print("SHYT_FSR_WINDOWS_CLANG64_FOUR_HOST_CPP_PATCH_PASS")


if __name__ == "__main__":
    main()
