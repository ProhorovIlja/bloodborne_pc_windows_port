#!/usr/bin/env python3
"""V20: validate byte ranges before allocating game map/archive IO buffers."""
from pathlib import Path

PATH = 'bbport/gpu/shim/bbport_map_charts.cpp'
HEADER_PATH = 'bbport/gpu/shim/sh_map_range_io.hpp'
HERE = Path(__file__).resolve().parent

def one(s, old, new, label):
    count = s.count(old)
    if count != 1:
        raise ValueError(f'V20 {label}: expected one source anchor, found {count}')
    return s.replace(old, new, 1)

def transform(s):
    if 'SH-MAP-RANGE-V20' in s:
        raise ValueError('V20 already applied')
    s = one(s, '#include "bbport_settings.h"',
            '#include "bbport_settings.h"\n#include "sh_map_range_io.hpp" // SH-MAP-RANGE-V20', 'header')
    old_range = '''std::vector<std::uint8_t> ReadGameRange(const std::string& relative, std::uint64_t offset, std::uint64_t size) {
    char path[1024];
    if (!bbcoop_game_file(("dvdroot_ps4/" + relative).c_str(), path, sizeof(path))) {
        return {};
    }
    std::ifstream file(std::filesystem::u8path(path), std::ios::binary);
    std::vector<std::uint8_t> bytes(size);
    file.seekg(std::streamoff(offset));
    file.read(reinterpret_cast<char*>(bytes.data()), std::streamsize(size));
    bytes.resize(std::size_t(std::max<std::streamsize>(0, file.gcount())));
    return bytes;
}'''
    new_range = '''std::vector<std::uint8_t> ReadGameRange(const std::string& relative, std::uint64_t offset, std::uint64_t size) {
    char path[1024];
    if (!bbcoop_game_file(("dvdroot_ps4/" + relative).c_str(), path, sizeof(path))) {
        return {};
    }
    return SeamlessHunt::MapIO::ReadExact(std::filesystem::u8path(path), offset, size);
}'''
    s = one(s, old_range, new_range, 'runtime game archive read')
    old_prepare = '''        std::ifstream file(root / relative, std::ios::binary);
        std::vector<std::uint8_t> bytes(size);
        file.seekg(std::streamoff(offset));
        file.read(reinterpret_cast<char*>(bytes.data()), std::streamsize(size));
        bytes.resize(std::size_t(std::max<std::streamsize>(0, file.gcount())));
        return bytes;'''
    new_prepare = '''        return SeamlessHunt::MapIO::ReadExact(root / relative, offset, size);'''
    s = one(s, old_prepare, new_prepare, 'launcher map preparation archive read')
    return s

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error('in-place source mutation prohibited')
    args.output.write_text(transform(args.source.read_text('utf-8')), encoding='utf-8')
