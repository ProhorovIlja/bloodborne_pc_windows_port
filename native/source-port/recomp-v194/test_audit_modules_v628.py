# SPDX-License-Identifier: GPL-2.0-or-later
from hashlib import sha256
import struct
import unittest
from unittest.mock import patch

import audit_modules_v628 as a


def fixture(provider=False, version=1):
    text = b'\0module\0library\0ExampleNID#B#C\0'
    symbols = bytes(24)+a.SYM.pack(16,0x12,0,int(provider),0x100 if provider else 0,0)
    plt = b'' if provider else a.RELA.pack(0x200,(1<<32)|7,0)
    parts = (text,symbols,plt,b'')
    tags = []
    offset = 0
    for part,(x,y) in zip(parts,((0x35,0x37),(0x39,0x3f),(0x29,0x2d),(0x2f,0x31))):
        tags += [(a.SCE+x,offset),(a.SCE+y,len(part))]
        offset += len(part)
    tags += [(a.SCE+(0x0d if provider else 0x0f),(2<<48)|(version<<32)|1),
             (a.SCE+(0x13 if provider else 0x15),(1<<48)|(1<<32)|8),(0,0)]
    dyn = b''.join(struct.pack('<QQ',*t) for t in tags)
    blob = b''.join(parts)
    h = struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01\x01',0xfe18,62,1,0,64,0,0,64,56,2,0,0,0)
    off = len(h)+2*a.PH.size
    return (h+a.PH.pack(2,4,off+len(blob),0,0,len(dyn),len(dyn),8)
            +a.PH.pack(a.SCE,4,off,0,0,len(blob)+len(dyn),0,8)+blob+dyn)


def wrap(elf, flags=0x100800):
    start = 64+2*a.PH.size
    prefix = bytearray(32)
    prefix[:4] = b'O\x15=\x1d'
    struct.pack_into('<H',prefix,24,1)
    n = len(elf)-start
    return bytes(prefix)+struct.pack('<QQQQ',flags,64+start,n,n)+elf


class TestModules(unittest.TestCase):
    def test_self_round_trip(self):
        elf = fixture()
        self.assertEqual(a.link_tables(elf),a.link_tables(wrap(elf)))
        for bad in (wrap(elf,0x100802),wrap(elf,0x100808),wrap(elf,0x300800),wrap(elf)[:-1]):
            with self.assertRaises(ValueError):
                a.link_tables(bad)

    def test_namespace_version_and_conflict(self):
        blobs = [fixture(),wrap(fixture(True)),wrap(fixture(True,2))]
        def scan():
            with patch.object(a,'PINS',tuple(sha256(b).hexdigest() for b in blobs)):
                return a.census(blobs)
        self.assertEqual(scan()['images']['eboot']['bindings'],{'libc:type2':1})
        blobs[1] = wrap(fixture(True,3))
        self.assertEqual(scan()['unresolved_unique'],1)
        blobs[1:] = [wrap(fixture(True))]*2
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            scan()
        with self.assertRaisesRegex(ValueError,'hash'):
            a.census(blobs)
