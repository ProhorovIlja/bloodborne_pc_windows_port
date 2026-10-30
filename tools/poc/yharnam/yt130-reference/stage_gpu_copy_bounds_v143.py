#!/usr/bin/env python3
"""V143 original native YT1.3 Vulkan copy bounds guard, source pinned.

Reviewed candidate shadPS4/shadPS4 #5561. In the actual original bbport
Runtime::CopyBuffer, validate source and destination offsets+lengths before
ALL barrier/range calculations and the recorded Vulkan copy. Preserve the
bbport >4-copies bounding optimization and the original scheduling path.
Only disposable checked-out game GPU C++ source, never live gameplay files.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = Path("bbport/gpu/shadps4/video_core/renderer_vulkan/vk_runtime.cpp")
BLOB = "4d7505de7c0381d48f2d4c98351d2ba3262b1183"
HEADER_OLD = '#include "common/alignment.h"\n'
HEADER_NEW = '#include <atomic>\n#include <vector>\n\n#include "common/alignment.h"\n'
METHOD_OLD = """void Runtime::CopyBuffer(const VideoCore::Buffer* src, const VideoCore::Buffer* dst,
                         std::span<const vk::BufferCopy> copies) {
    scheduler.EndRendering();

    // bbport: many regions (HLE copy shaders) are tracked as one bounding range per buffer:
"""
METHOD_NEW = """void Runtime::CopyBuffer(const VideoCore::Buffer* src, const VideoCore::Buffer* dst,
                         std::span<const vk::BufferCopy> copies) {
    scheduler.EndRendering();

    // SHYT-V143: guest descriptors can transiently exceed a source or
    // destination buffer; issuing those copies can lose the Vulkan device.
    // Validate BEFORE both the batched barrier range and the recorded copy.
    // Avoid overflow in offset+size (subtract only after offset <= capacity).
    const auto valid_copy = [&](const vk::BufferCopy& copy) {
        const u64 src_size = src->SizeBytes();
        const u64 dst_size = dst->SizeBytes();
        return copy.srcOffset <= src_size && copy.size <= src_size - copy.srcOffset &&
               copy.dstOffset <= dst_size && copy.size <= dst_size - copy.dstOffset;
    };
    std::vector<vk::BufferCopy> filtered;
    bool invalid = false;
    for (const auto& copy : copies) {
        if (!valid_copy(copy)) {
            invalid = true;
            break;
        }
    }
    if (invalid) {
        filtered.reserve(copies.size());
        for (const auto& copy : copies) {
            if (valid_copy(copy)) {
                filtered.push_back(copy);
            } else {
                static std::atomic<u32> warned{0};
                if (warned.fetch_add(1, std::memory_order_relaxed) < 16) {
                    LOG_WARNING(Render_Vulkan, "Dropping out-of-bounds Vulkan buffer copy");
                }
            }
        }
        copies = filtered;
    }
    if (copies.empty()) {
        return;
    }

    // bbport: many regions (HLE copy shaders) are tracked as one bounding range per buffer:
"""

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()

def normalized(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n")

def rewrite(source: str) -> str:
    for old, new in ((HEADER_OLD, HEADER_NEW), (METHOD_OLD, METHOD_NEW)):
        if source.count(old) != 1:
            raise ValueError("V143 original GPU copy source drift or already staged: " + old[:58])
        source = source.replace(old, new, 1)
    # The old original bbport copies span must STILL be used by all existing
    # optimized barrier/record sections. The change only filters it upfront.
    for anchor in (
        "const bool bounded = copies.size() > 4;",
        "for (const auto& copy : copies) {",
        "regions = scheduler.RecordData(copies)",
        "src_max = std::max<u64>(src_max, copy.srcOffset + copy.size);",
        "dst_max = std::max<u64>(dst_max, copy.dstOffset + copy.size);",
    ):
        if anchor not in source:
            raise ValueError("V143 original Vulkan barrier/record code drift: " + anchor)
    return source

def transform(raw: bytes) -> bytes:
    original = normalized(raw)
    if git_blob(original) != BLOB:
        raise ValueError("V143 not exact pinned original YT1.3 vk_runtime.cpp")
    return rewrite(original.decode("utf-8")).encode("utf-8")

def stage(root: Path) -> None:
    target = root.resolve() / PATH
    if not target.is_file() or target.is_symlink():
        raise ValueError("V143 original GPU C++ regular file required")
    target.write_bytes(transform(target.read_bytes()))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_gpu_copy_bounds_v143.py PINNED_DISPOSABLE_YT_ROOT")
    stage(Path(sys.argv[1]))
    print("SHYT_V143_ORIGINAL_GPU_VULKAN_COPY_BUFFER_BOUNDS_STAGED_NO_REAL_GAMEPLAY")
