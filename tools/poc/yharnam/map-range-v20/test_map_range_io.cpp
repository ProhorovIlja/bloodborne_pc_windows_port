#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_map_range_io.hpp"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
int main() {
    namespace fs = std::filesystem;
    const auto path = fs::temp_directory_path() / "sh_map_range_io_unit_fixture.bin";
    {
        std::ofstream file(path, std::ios::binary | std::ios::trunc);
        assert(file);
        file.write("ABCDEFGH", 8);
    }
    using SeamlessHunt::MapIO::ReadExact;
    auto bytes = ReadExact(path, 2, 3);
    assert(std::string(bytes.begin(), bytes.end()) == "CDE");
    bytes = ReadExact(path, 0, 8);
    assert(bytes.size() == 8 && bytes.front() == 'A' && bytes.back() == 'H');
    assert(ReadExact(path, 0, 0).empty());
    assert(ReadExact(path, 7, 2).empty());
    assert(ReadExact(path, 8, 1).empty());
    assert(ReadExact(path, 9, 1).empty());
    assert(ReadExact(path, std::numeric_limits<std::uint64_t>::max()-1, 6).empty());
    assert(ReadExact(path, 0, SeamlessHunt::MapIO::MaxRangeBytes + 1).empty());
    assert(ReadExact(path.parent_path() / "sh_map_range_missing_unit_file", 0, 1).empty());
    // Exhaustive small-range test matrix: both valid reads and rejected spans.
    for (std::uint64_t off = 0; off != 13; ++off) {
        for (std::uint64_t len = 0; len != 13; ++len) {
            const auto got = ReadExact(path, off, len);
            const bool valid = len != 0 && off <= 8 && len <= 8 - off;
            if (!valid) { assert(got.empty()); continue; }
            assert(got.size() == len);
            for (std::uint64_t i = 0; i < len; ++i)
                assert(got[static_cast<std::size_t>(i)] == static_cast<std::uint8_t>('A' + off + i));
        }
    }
    fs::remove(path);
    std::cout << "PASS: exact game-file range I/O and malformed offset/length guards\n";
}
