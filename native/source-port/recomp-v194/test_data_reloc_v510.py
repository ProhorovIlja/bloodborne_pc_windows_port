# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from data_reloc_v510 import partition

RX = (1, 5, 0, 0x100, 0, 64, 64, 1)
RW = (1, 6, 64, 0x200, 0, 32, 64, 1)


class TestDataReloc(unittest.TestCase):
    def test_relative_and_imports(self):
        rows = {0x218: (1 << 32 | 1, -12), 0x208: (8, 0x110),
                0x230: (2 << 32 | 7, 0), 0x200: (3 << 32 | 6, 0)}
        self.assertEqual(partition([RX, RW], RW, rows, 0x400000),
                         ([(8, 0x400110)], [(0, 3, 6, 0), (24, 1, 1, -12), (48, 2, 7, 0)]))

    def test_refuses_unknown_or_inconsistent_metadata(self):
        for rows in ({0x100: (8, 0x100)}, {0x23c: (8, 0x100)}, {0x200: (8, 0x180)},
                     {0x200: (8, 0x100), 0x207: (8, 0x100)}, {0x200: (1 << 32 | 8, 0x100)},
                     {0x200: (1 << 32 | 7, 1)}, {0x200: (7, 0)}, {0x200: (16, 0)}):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                partition([RX, RW], RW, rows)
        with self.assertRaises(ValueError):
            partition([RX, RW], RW, {}, (1 << 64)-0x200)
