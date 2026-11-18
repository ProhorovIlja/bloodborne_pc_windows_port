# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline-only CUSA03173 1.09 SELF/ELF parity and RELA dependency audit.

No extraction, executable mapping, or output of addresses or original bytes.
Not a general SELF parser: encrypted/compressed/unknown entries fail closed.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import Struct, iter_unpack, unpack_from

SELF_SHA = 'd65f0b4f01d59166aed16f8604196d8b7dd805abbf0758b356e8f1354c9429f9'
ELF_SHA = '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7'
PH = Struct('<II6Q')


def require(ok, why):
    if not ok:
        raise ValueError(why)


def span(data, offset, size):
    require(0 <= offset <= len(data) and 0 <= size <= len(data)-offset, 'invalid span')
    return memoryview(data)[offset:offset+size]


def audit(self, elf):
    require(self[:4] == b'\x4f\x15\x3d\x1d' and elf[:6] == b'\x7fELF\x02\x01', 'wrong format')
    require(len(self) >= 32 and len(elf) >= 64, 'short header')
    require(unpack_from('<H', self, 24)[0] == 8, 'unexpected SELF entry count')
    require(unpack_from('<Q', elf, 32)[0] == 64 and unpack_from('<HH', elf, 54) == (56,10), 'unexpected ELF headers')
    end = 64 + 10*PH.size
    require(span(self,288,end) == span(elf,0,end), 'ELF header mismatch')
    ph = list(PH.iter_unpack(span(elf,64,end-64)))
    chunks = [(0,end)]
    seen = set()
    for props, src, size, mem in iter_unpack('<4Q', span(self,32,256)):
        idx = props >> 20
        require(idx < len(ph), 'invalid SELF segment index')
        if props & 0xfffff == 0x10004:
            span(self,src,size)
            continue
        require(props & 0xfffff == 0x2804 and idx not in seen, 'unsupported SELF segment')
        off, n = ph[idx][2], ph[idx][5]
        require(size == mem == n and span(self,src,n) == span(elf,off,n), 'segment mismatch')
        chunks.append((off,off+n))
        seen.add(idx)
        if idx == 8:
            require(ph[9][0] == 0x6fffff01, 'unexpected trailer type')
            t, n = ph[9][2], ph[9][5]
            require(t == off+size and t+n == len(elf) and src+size+n == len(self), 'unexpected trailer placement')
            require(span(self,src+size,n) == span(elf,t,n), 'trailer mismatch')
            chunks.append((t,t+n))
    require(seen == {0,1,7,8}, 'missing primary SELF entry')
    cursor = padding = 0
    for start, stop in sorted(chunks):
        require(start >= cursor and not any(span(elf,cursor,start-cursor)), 'nonzero padding or overlap')
        padding += start-cursor
        cursor = stop
    require(cursor == len(elf), 'incomplete ELF coverage')
    require(ph[3][0] == 2 and ph[7][0] == 0x61000000, 'missing dynamic metadata')
    tags = dict(iter_unpack('<2Q', span(elf,ph[3][2],ph[3][5])))
    off, size = tags[0x6100002f], tags[0x61000031]
    require(tags[0x61000033] == 24 and size % 24 == 0 and off+size <= ph[7][5], 'invalid SCE RELA span')
    counts = Counter(elf_bytes=cursor, zero_padding=padding, self_entries=len(seen), elf_tail_bytes=ph[9][5])
    def segment(addr, width):
        for idx, name in ((0,'rx'),(1,'rw')):
            lo, size = ph[idx][3], ph[idx][6]
            if lo <= addr <= lo+size-width:
                return name
        return 'outside'
    for dst, info, addend in iter_unpack('<QQq', span(elf,ph[7][2]+off,size)):
        kind = info & 0xffffffff
        counts[f'rela_type_{kind}'] += 1
        if kind == 8:
            require(info == 8, 'unexpected symbol on RELATIVE relocation')
            counts[f'relative_{segment(dst,8)}_to_{segment(addend,1)}'] += 1
    return dict(counts)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('self',type=Path)
    p.add_argument('elf',type=Path)
    a = p.parse_args()
    require((a.self.stat().st_size,a.elf.stat().st_size) == (93825704,93667640), 'unexpected input size')
    s,e = a.self.read_bytes(),a.elf.read_bytes()
    require(sha256(s).hexdigest() == SELF_SHA and sha256(e).hexdigest() == ELF_SHA, 'unexpected input identity')
    print(json.dumps(audit(s,e),sort_keys=True))
