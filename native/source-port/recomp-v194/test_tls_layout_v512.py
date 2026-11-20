# SPDX-License-Identifier: GPL-2.0-or-later
import unittest
from tls_layout_v512 import initialize, plan


def image(size, align, data=b'abc', reloc=()):
    rw = dict(type=1, flags=6, vaddr=256, offset=0, filesz=128, memsz=256)
    tls = dict(type=7, flags=4, vaddr=256, offset=0, filesz=len(data), memsz=size, align=align)
    marker = dict(name='', type=3, binding=0, section=0, value=0, size=0)
    return dict(ph=[rw,tls], elf=data+bytes(128-len(data)), symbols=[{},marker], relocs=reloc)


class TestTLS(unittest.TestCase):
    def test_alignment_and_private_threads(self):
        blocks, slots = plan({'main':image(19,16), 'mod':image(64,32,b'x',[(336,16,1,0)])})
        self.assertEqual([b[1:5] for b in blocks], [(1,32,19,16),(2,96,64,32)])
        self.assertEqual(slots, {('mod',80):2})
        a,tp = initialize(blocks)
        b,_ = initialize(blocks)
        self.assertEqual((tp,a[tp-32:tp-32+19],a[:64]),(96,b'abc'+bytes(16),b'x'+bytes(63)))
        a[0] = 0
        self.assertEqual(b[0],120)

    def test_rejects_nonlocal_and_unsupported(self):
        for row in [(256,16,1,0),(336,17,1,0),(336,16,2,0),(336,16,1,1),(505,16,1,0)]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                plan({'main':image(19,16,reloc=[row])})
        bad = image(19,16,reloc=[(336,16,1,0)])
        bad['symbols'][1]['name'] = 'other'
        with self.assertRaises(ValueError):
            plan({'main':bad})
