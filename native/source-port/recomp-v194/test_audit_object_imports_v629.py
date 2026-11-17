# SPDX-License-Identifier: GPL-2.0-or-later
import unittest

from audit_object_imports_v629 import audit, inventory, location


class Objects(unittest.TestCase):
    def test_data_bindings(self):
        loads = [(1,5,0,0x100,0,0x80,0x80,16),(1,6,0,0x200,0,0x80,0x100,16)]
        game = {'imports': {'vt': [(0x10,1,16),(0x18,6,0)], 'call': [(0x20,7,0)]}}
        lib = {'exports': {'vt': {(1,0x210,48)}, 'call': {(2,0x110,16)}},
               'relocations': [(0x210,8,0x110),(0x218,8,0x280),(0x240,8,0x280)]}
        r = inventory(game,lib,loads)
        self.assertEqual(r['objects'],1)
        self.assertEqual(r['import_sites'],{1:1,6:1})
        self.assertEqual(r['import_addends'],{'nonzero':1,'zero':1})
        self.assertEqual(r['object_relocations'],{8:2})
        self.assertEqual(r['relative_targets'],{'rx_file':1,'zero_fill':1})
        self.assertEqual(location(loads,0x278,16),'mixed')
        with self.assertRaises(ValueError):
            location(loads,0x2f8,16)
        with self.assertRaises(ValueError):
            location(loads+loads,0x110,1)
        lib['exports']['vt'].add((1,0x220,48))
        with self.assertRaises(ValueError):
            inventory(game,lib,loads)

    def test_unpinned(self):
        with self.assertRaisesRegex(ValueError,'hash'):
            audit(b'not retail',b'not a PRX')
