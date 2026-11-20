# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest

from audit_rtti_graph_v636 import graph


class GraphTest(unittest.TestCase):
    def setUp(self):
        self.blob = bytearray(256)
        struct.pack_into('<II', self.blob, 144, 0, 2)
        struct.pack_into('<q', self.blob, 160, 2)
        struct.pack_into('<q', self.blob, 176, -254)
        self.records = {0: 'plain', 64: 'single', 128: 'multiple'}
        self.reloc = {8: 220, 72: 228, 136: 236, 80: 0, 152: 0, 168: 64}

    def run_graph(self):
        return graph(self.records, self.reloc, lambda a, n: self.blob[a:a+n])

    def test_graph(self):
        self.assertEqual(self.run_graph(), dict(plain=1, single=1, multiple=1,
                                               base_edges=3, public_edges=2, virtual_edges=0))

    def test_cycle(self):
        self.reloc[80] = 128
        with self.assertRaisesRegex(ValueError, 'cycle'):
            self.run_graph()

    def test_missing_base(self):
        del self.reloc[168]
        with self.assertRaisesRegex(ValueError, 'base not'):
            self.run_graph()

    def test_bad_count(self):
        struct.pack_into('<I', self.blob, 148, 65)
        with self.assertRaisesRegex(ValueError, 'header'):
            self.run_graph()
