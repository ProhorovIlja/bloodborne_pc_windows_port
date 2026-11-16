# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest
from switch_scan_v506 import recover


def fixture():
    image = bytearray(b'\x90' * 96)
    image[8:30] = bytes.fromhex('4883f8027716488d152b00000048630c824801d1ffe1')
    struct.pack_into('<iii', image, 64, -32, -16, -32)
    return image


class TestRecover(unittest.TestCase):
    def test_slide_and_duplicate(self):
        for base in (0, 0x800000000):
            self.assertEqual(recover(fixture(), base, base+8, {base+32, base+36, base+48}),
                             (base+64, base+36, (base+32, base+48, base+32)))

    def test_corruption(self):
        for pos, value in ((11, 128), (12, 0x76), (13, 0), (17, 0), (29, 0xe0), (64, 0)):
            image = fixture()
            image[pos] = value
            with self.subTest(pos=pos), self.assertRaises(ValueError):
                recover(image, 0, 8, {32, 36, 48})
        for image, blocks in ((fixture()[:75], {32, 36, 48}), (fixture(), {32, 48}), (fixture(), {32, 36})):
            with self.assertRaises(ValueError):
                recover(image, 0, 8, blocks)
