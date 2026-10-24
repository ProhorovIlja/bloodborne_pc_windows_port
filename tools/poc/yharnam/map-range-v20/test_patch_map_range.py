import unittest
from patch_map_range import transform

SOURCE='''#include "bbport_settings.h"
std::vector<std::uint8_t> ReadGameRange(const std::string& relative, std::uint64_t offset, std::uint64_t size) {
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
}
        std::ifstream file(root / relative, std::ios::binary);
        std::vector<std::uint8_t> bytes(size);
        file.seekg(std::streamoff(offset));
        file.read(reinterpret_cast<char*>(bytes.data()), std::streamsize(size));
        bytes.resize(std::size_t(std::max<std::streamsize>(0, file.gcount())));
        return bytes;
'''

class Tests(unittest.TestCase):
    def test_both_readers_use_exact_bounds(self):
        result = transform(SOURCE)
        self.assertIn('SH-MAP-RANGE-V20', result)
        self.assertEqual(result.count('SeamlessHunt::MapIO::ReadExact('), 2)
        self.assertNotIn('std::vector<std::uint8_t> bytes(size)', result)
        self.assertEqual(SOURCE.count('std::vector<std::uint8_t> bytes(size)'), 2)
    def test_fails_closed_source_drift(self):
        with self.assertRaisesRegex(ValueError, 'launcher map preparation archive read'):
            transform(SOURCE.replace('std::ifstream file(root / relative', 'std::ifstream file(root / file'))
    def test_double_apply_fails(self):
        with self.assertRaisesRegex(ValueError, 'already applied'):
            transform(transform(SOURCE))
    def test_unchanged_original(self):
        initial=SOURCE
        transform(initial)
        self.assertEqual(initial, SOURCE)

if __name__=='__main__': unittest.main()
