#!/usr/bin/env python3
"""V142: exact-original YT1.3 GPU image layer/slice zero-divisor guard.

Backport limited defensive logic from shadPS4 PR #5560 into the pinned
native Windows GPU ImageInfo implementation. Source-only, fail-closed.
Does not alter the renderer for valid nonzero sizes. No gameplay, server,
save, network or production files changed.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

ORIGINAL_PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = Path("bbport/gpu/shadps4/video_core/texture_cache/image_info.cpp")
BLOB = "5b99e73b112824e1c289c25372b481f49eb89fa8"
EDITS = (
    ('#include "common/assert.h"\n',
     '#include <algorithm>\n\n#include "common/assert.h"\n'),
    ('    ASSERT_MSG(array_mode != AmdGpu::ArrayMode::ArrayLinearGeneral,\n'
     '               "Unhandled array mode: ArrayLinearGeneral");\n',
     '    ASSERT_MSG(array_mode != AmdGpu::ArrayMode::ArrayLinearGeneral,\n'
     '               "Unhandled array mode: ArrayLinearGeneral");\n'
     '    if (resources.layers == 0) {\n'
     '        LOG_WARNING(Render_Vulkan, "Image with zero layers, using 1");\n'
     '        resources.layers = 1;\n'
     '    }\n'),
    ('        const u32 slice_size = mip_size / info.resources.layers;\n',
     '        const u32 slice_size =\n'
     '            info.resources.layers != 0 ? mip_size / info.resources.layers : mip_size;\n'
     '        if (slice_size == 0) {\n'
     '            continue;\n'
     '        }\n'),
    ('    const u32 slice_size = info.mips_layout[mip].size / info.resources.layers;\n'
     '    if (guest_size % slice_size != 0) {\n',
     '    const u32 layers = std::max<u32>(info.resources.layers, 1);\n'
     '    const u32 slice_size = info.mips_layout[mip].size / layers;\n'
     '    if (slice_size == 0 || guest_size % slice_size != 0) {\n'),
)

def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()

def normalize(raw: bytes) -> bytes:
    # Windows checkout line endings are accepted only if the normalized
    # source exactly matches the original immutable Git blob.
    return raw.replace(b"\r\n", b"\n")

def rewrite(source: str) -> str:
    for old, new in EDITS:
        if source.count(old) != 1:
            raise ValueError("V142 original YT1.3 image_info source drift/duplicate: " + old[:55])
        source = source.replace(old, new, 1)
    if source.count("const u32 slice_size = info.mips_layout[mip].size / info.resources.layers;"):
        raise ValueError("V142 stale raw layer divisor remains")
    return source

def transform(raw: bytes) -> bytes:
    src = normalize(raw)
    if blob_sha(src) != BLOB:
        raise ValueError("V142 original GPU blob hash mismatch: " + blob_sha(src))
    return rewrite(src.decode("utf-8")).encode("utf-8")

def stage(root: Path) -> None:
    target = root.resolve() / PATH
    if not target.is_file() or target.is_symlink():
        raise ValueError("V142 expected regular original GPU source")
    target.write_bytes(transform(target.read_bytes()))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_gpu_zero_slice_v142.py PINNED_DISPOSABLE_YT_ROOT")
    stage(Path(sys.argv[1]))
    print("SHYT_V142_ORIGINAL_GPU_ZERO_LAYERS_AND_SLICE_GUARD_STAGED_NO_REAL_GAMEPLAY")
