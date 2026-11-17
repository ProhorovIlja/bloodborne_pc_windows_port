# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import unittest

from audit_imports_v627 import audit, indexed_plt


def fixture(va):
    slots = [va+0x280,va+0x298,va+0x290]
    code = bytearray(b'\xff\x35'+b'\0'*4+b'\xff\x25'+b'\0'*8)
    for i,slot in enumerate(slots):
        p = len(code)
        code.extend(struct.pack('<2siBiBi',b'\xff\x25',slot-va-p-6,0x68,i,0xe9,-p-16))
    return code,[(slot,((i+1)<<32)|7,0) for i,slot in enumerate(slots)]


class Audit(unittest.TestCase):
    def test_nonmonotonic_slots(self):
        for va in (0,0x400000):
            code,rel = fixture(va)
            self.assertEqual(indexed_plt(code,va,rel),[va+16,va+32,va+48])

    def test_reject_modified_entries(self):
        code,rel = fixture(0)
        for offset in (0,6,16,32+2,32+6,32+7,48+11,48+12):
            bad = bytearray(code)
            bad[offset] ^= 1
            with self.subTest(offset=offset),self.assertRaises(ValueError):
                indexed_plt(bad,0,rel)
        with self.assertRaises(ValueError):
            indexed_plt(code[:-1],0,rel)
        with self.assertRaises(ValueError):
            indexed_plt(code,0,rel[::-1])

    def test_unpinned_input(self):
        with self.assertRaisesRegex(ValueError,'unsupported executable hash'):
            audit(b'\x7fELF')


if __name__=='__main__':
    unittest.main()
