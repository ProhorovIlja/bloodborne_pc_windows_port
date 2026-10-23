#!/usr/bin/env python3
"""V19: bound persisted BBMAP9/BBMESH1 decompression and prevent archive range overflow."""
from pathlib import Path
PATH = 'bbport/gpu/shim/bbport_map_art.cpp'

def one(s, old, new, name):
    count=s.count(old)
    if count!=1: raise ValueError(f'V19 {name}: expected one source anchor, found {count}')
    return s.replace(old,new,1)

def transform(s):
    if 'SH-MAP-DATA-V19' in s: raise ValueError('V19 already applied')
    s=one(s,
'''    if (chart.width <= 0 || chart.height <= 0 || chart.width > 8192 || chart.height > 8192 ||
        !(chart.ppm > 0.0f) || stored > file.size() - 32) {''',
'''    // SH-MAP-DATA-V19: never expand a damaged cache file into hundreds of MiB
    // above the supported map generator's 6144px maximum per dimension.
    constexpr std::uint64_t MaxPixels = 48ull * 1024 * 1024;
    if (chart.width <= 0 || chart.height <= 0 || chart.width > 8192 || chart.height > 8192 ||
        !std::isfinite(chart.ppm) || !(chart.ppm > 0.0f) ||
        (std::uint64_t(chart.width) * std::uint64_t(chart.height) > MaxPixels) ||
        stored > file.size() - 32) {''', 'chart RGBA allocation bound')
    s=one(s,
'''    if (s.width < 0 || s.height < 0 || s.width > 8192 || s.height > 8192 || storeys_stored > file.size() - at) {''',
'''    // Existing maps draw floors at FloorCell=2. Reject corrupt storey headers
    // before constructing three huge arrays and the decompression buffer.
    constexpr std::uint64_t MaxFloorCells = 12ull * 1024 * 1024;
    if (s.width < 0 || s.height < 0 || s.width > 8192 || s.height > 8192 ||
        s.width > (chart.width + Chart::FloorCell - 1) / Chart::FloorCell ||
        s.height > (chart.height + Chart::FloorCell - 1) / Chart::FloorCell ||
        std::uint64_t(s.width) * std::uint64_t(s.height) > MaxFloorCells ||
        storeys_stored > file.size() - at) {''', 'storeys allocation bound')
    s=one(s,
'''    std::memcpy(s.roof.data(), raw.data(), cells * 2);
    std::memcpy(s.level.data(), raw.data() + cells * 2, cells * Chart::Levels * 2);
    std::memcpy(s.rgb.data(), raw.data() + cells * 2 + cells * Chart::Levels * 2, cells * Chart::Levels * 4);''',
'''    if (cells != 0) {
        std::memcpy(s.roof.data(), raw.data(), cells * 2);
        std::memcpy(s.level.data(), raw.data() + cells * 2, cells * Chart::Levels * 2);
        std::memcpy(s.rgb.data(), raw.data() + cells * 2 + cells * Chart::Levels * 2, cells * Chart::Levels * 4);
    }''', 'zero-cell memcpy avoidance')
    s=one(s,
'''    if (stored > file.size() - 16 || raw_size < 8 || raw_size > (1u << 31)) {''',
'''    // A corrupt BBMESH1 header must not force a multi-gigabyte allocation.
    if (stored > file.size() - 16 || raw_size < 8 || raw_size > (512u << 20)) {''', 'mesh decompression bound')
    s=one(s,
'''            if (entry.offset + entry.size > bdt.size()) {''',
'''            // Overflow-safe check for untrusted archive index offset/size.
            if (entry.offset > bdt.size() || entry.size > bdt.size() - entry.offset) {''', 'archive overflow')
    return s

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args()
    if args.source.resolve()==args.output.resolve():p.error('source overwrite refused')
    args.output.write_text(transform(args.source.read_text('utf-8')),encoding='utf-8')
