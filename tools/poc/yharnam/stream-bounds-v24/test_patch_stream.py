import unittest
from patch_stream import transform
SOURCE='''#include "coop/game_link.h"
            partial.clear();
            restarted = true;
            partial.insert(partial.end(), chunk.begin() + 1, chunk.end());
            if ((chunk[0] & LastChunk) != 0) {
                messages.push_back(std::exchange(partial, {}));
            }
    std::vector<u8> partial;
'''
class TestStream(unittest.TestCase):
    def test_per_peer_bound_and_reset(self):
        s=transform(SOURCE)
        self.assertIn('SH-STREAM-BOUNDS-V24',s)
        self.assertIn('partial.Reset();',s)
        self.assertIn('partial.Push(',s)
        self.assertIn('StreamBounds::Assembler partial',s)
        self.assertNotIn('partial.insert(',s)
    def test_upstream_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,'bounded reassembly'):
            transform(SOURCE.replace('chunk.begin() + 1','chunk.begin() + 2'))
    def test_double_apply_rejected(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
    def test_original_unchanged(self):
        before=SOURCE
        transform(before);self.assertEqual(before,SOURCE)
if __name__=='__main__':unittest.main()
