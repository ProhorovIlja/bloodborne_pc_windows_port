# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest
from ctor_v519 import extract


class TestCtor(unittest.TestCase):
    def test_exact_shape_and_bounds(self):
        raw = bytearray.fromhex('488d0500000000803800751c488d0d000000004883c110'
                                '488d150000000048890a48c70001000000c3')
        for p, d in ((3, 512-256-7), (15, 400-256-35), (26, 520-256-30)):
            struct.pack_into('<i', raw, p, d)
        self.assertEqual(extract(raw,256,512,16,528), (0,8,400))
        with self.assertRaises(ValueError):
            extract(raw,256,512,15,528)
        with self.assertRaises(ValueError):
            extract(raw,255,512,16,528)
        raw[11] ^= 1
        self.assertIsNone(extract(raw,256,512,16,528))
