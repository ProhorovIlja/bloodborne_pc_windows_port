#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V447: source-exact, OPT-IN patch of genuine CLS YT 1.4.0 BBHost host loader.

The original behavior stays the default. A candidate experimental env switch
BB_YT_FASTMEM_V447=1 uses BBHost's existing guest map generation and snapshot,
with actual CPU rights and no fake 'guest RW' classification of the host stack.

Copies ONLY 2 modified/public source files into an isolated output directory.
It does not compile game code, test game boot, change production or edit saves.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile

from verify_cls_yt_bbhost_source_v441 import verify

PINNED_HOST_SHA256 = "2223da0a3939fe0ba1218e47bfe3be1c0d585aa05558a6297f4077f80403a67e"
INCLUDE = '#include "yt/yt_host.h"\n'
GEN = """    static thread_local std::uint64_t generation = 0;
    ++generation;
    return &generation;"""
GEN_NEW = """    static thread_local std::uint64_t generation = 0;
    static const bool opt_in = [] {
        const char* e = std::getenv("BB_YT_FASTMEM_V447");
        return e && e[0] == '1' && e[1] == '\\0';
    }();
    if (opt_in) {
        // Real BBHost g_maps_gen, not a fabricated per-query generation.
        generation = hle_kernel_maps_generation();
    } else {
        ++generation;  // original CLS behavior and default
    }
    return &generation;"""
PROTECTION = """    if (slow) return 0;
    constexpr std::uint32_t kRead = 1, kWrite = 2;"""
PROTECTION_NEW = """    if (slow) return 0;
    static const bool opt_in = [] {
        const char* e = std::getenv("BB_YT_FASTMEM_V447");
        return e && e[0] == '1' && e[1] == '\\0';
    }();
    if (opt_in) {
        // Only guest mappings enter YT's MemoryWindows cached as 'guest'.
        // Host stack and other Windows memory use original VirtualQuery
        // fallback (guest=false), not the old fabricated RW stack region.
        static thread_local BloodborneCoop::SHYT::MemoryV447::
            GuestMapCache<GuestMapInfo> maps;
        return maps.Query(
            address, start, end, prot,
            [] {return hle_kernel_maps_generation();},
            [](std::vector<GuestMapInfo>& out) {hle_kernel_snapshot_maps(out);}) ? 1 : 0;
    }
    // Default behavior stays BYTE-FOR-BYTE equivalent to original.
    constexpr std::uint32_t kRead = 1, kWrite = 2;"""
def replace_one(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError("original CLS v1.4.0 game loader source anchor drift")
    return source.replace(old, new, 1)

def patched(text: str) -> str:
    text = replace_one(text, INCLUDE,
                       INCLUDE + '#include "yt/shyt_yt_guest_memory_v447.h"\n')
    text = replace_one(text, GEN, GEN_NEW)
    text = replace_one(text, PROTECTION, PROTECTION_NEW)
    if text.count("BB_YT_FASTMEM_V447") != 2 or text.count("hle_kernel_maps_generation()") != 2:
        raise ValueError("V447 overlay structure unexpectedly changed")
    if text.count("hle_kernel_va_readable_in(address, 1, &lo, &hi)") != 1:
        raise ValueError("default original BBHost memory path removed")
    return text

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    a = p.parse_args()
    source_header = Path(__file__).with_name("shyt_yt_bbhost_guest_memory_v447.h")
    if not source_header.is_file() or source_header.is_symlink():
        raise SystemExit("V447_CANDIDATE_REFUSED_UNVERIFIED_HELPER")
    if a.output_dir.is_symlink() or a.output_dir.exists():
        raise SystemExit("V447_CANDIDATE_REFUSED_EXISTING_OUTPUT")
    with tempfile.TemporaryDirectory(prefix="shyt-v447-") as temp:
        scratch = Path(temp)
        verify(a.archive, extract_to=scratch)
        host_file = scratch / "yt_host.cpp"
        original = host_file.read_bytes()
        if hashlib.sha256(original).hexdigest() != PINNED_HOST_SHA256:
            raise SystemExit("V447_CANDIDATE_REFUSED_UNPINNED_ACTUAL_HOST")
        target = patched(original.decode("utf-8"))
        a.output_dir.mkdir(parents=True, exist_ok=False)
        (a.output_dir / "yt_host.cpp").write_text(target, encoding="utf-8")
        shutil.copyfile(source_header, a.output_dir / "shyt_yt_guest_memory_v447.h")
    print("SHYT_V447_CLS_140_BBHOST_MAP_EPOCH_OPT_IN_ONLY_SOURCE_OVERLAY_PASS")
    print("SHYT_V447_NO_DEFAULT_BEHAVIOR_CHANGE_NO_PROPRIETARY_GAME_FILES")

if __name__ == "__main__":
    main()
