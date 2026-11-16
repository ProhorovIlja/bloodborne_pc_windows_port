# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest
from switch_guard_v508 import candidates


class TestGuard(unittest.TestCase):
    def test_short_and_near_guard(self):
        for guard, body in [('83f9027715', '488d150000000048630c8a4801d1ffe1'),
                            ('83ff020f8711000000', '4c8d050000000049633cb84c01c7ffe7')]:
            image = bytearray(96)
            code = bytes.fromhex(guard + body)
            lea = len(bytes.fromhex(guard))
            image[:len(code)] = code
            struct.pack_into('<i', image, lea+3, 64-lea-7)
            struct.pack_into('<iii', image, 64, -32, -24, -32)
            self.assertEqual(list(candidates(image, 256, 256, 304)),
                             [(256, 320, 282, (288, 296, 288))])
            self.assertEqual(list(candidates(image, 256, 256, 288)), [])
            image[1] ^= 1
            self.assertEqual(list(candidates(image, 256, 256, 304)), [])
