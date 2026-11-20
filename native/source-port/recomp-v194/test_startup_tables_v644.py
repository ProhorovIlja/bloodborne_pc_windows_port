# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest
from audit_startup_tables_v644 import identify


class StartupTablesTest(unittest.TestCase):
    def setUp(self):
        self.rows = {32 + i*8: 120 + i*8 for i in range(7)}
        self.data = bytearray(256)
        self.data[136:144] = b'\x48\x8d\x05' + struct.pack('<i', 200-143) + b'\xc3'
        self.data[200:209] = b'iostream\0'

    def identify(self):
        return identify(32, self.rows, lambda a: 120 <= a < 176,
                        lambda a, n: self.data[a:a+n])

    def test_table(self):
        self.assertEqual(self.identify(), (2, tuple(range(120, 176, 8))))

    def test_missing_and_noncode(self):
        for target in (None, 200):
            self.rows[80] = target
            with self.assertRaisesRegex(ValueError, 'executable'):
                self.identify()

    def test_header(self):
        self.data[16] = 1
        with self.assertRaisesRegex(ValueError, 'header'):
            self.identify()

    def test_name(self):
        self.data[208] = ord('x')
        with self.assertRaisesRegex(ValueError, 'category'):
            self.identify()
