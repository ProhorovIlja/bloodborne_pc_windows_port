import unittest
from patch_map_data import transform
SOURCE='''    if (chart.width <= 0 || chart.height <= 0 || chart.width > 8192 || chart.height > 8192 ||
        !(chart.ppm > 0.0f) || stored > file.size() - 32) {
    if (s.width < 0 || s.height < 0 || s.width > 8192 || s.height > 8192 || storeys_stored > file.size() - at) {
    std::memcpy(s.roof.data(), raw.data(), cells * 2);
    std::memcpy(s.level.data(), raw.data() + cells * 2, cells * Chart::Levels * 2);
    std::memcpy(s.rgb.data(), raw.data() + cells * 2 + cells * Chart::Levels * 2, cells * Chart::Levels * 4);
    if (stored > file.size() - 16 || raw_size < 8 || raw_size > (1u << 31)) {
            if (entry.offset + entry.size > bdt.size()) {
'''
class Tests(unittest.TestCase):
    def test_limits_and_ranges(self):
        s=transform(SOURCE)
        for needle in ['MaxPixels = 48ull', 'MaxFloorCells = 12ull', 'std::isfinite(chart.ppm)', 'if (cells != 0)', '512u << 20','entry.offset > bdt.size()', 'entry.size > bdt.size() - entry.offset']:
            self.assertIn(needle,s)
        self.assertNotIn('raw_size > (1u << 31)',s)
    def test_rejects_source_drift(self):
        with self.assertRaisesRegex(ValueError,'archive overflow'):
            transform(SOURCE.replace('entry.offset + entry.size','entry.offset + entry.length'))
    def test_fails_double_apply(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
    def test_does_not_change_input(self):
        original=SOURCE;transform(original);self.assertEqual(original,SOURCE)
if __name__=='__main__': unittest.main()
