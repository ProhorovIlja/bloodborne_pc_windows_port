# SPDX-License-Identifier: GPL-2.0-or-later
"""Audit donor functions.tsv against independent seeds from the attested ELF.

A seed inside a scanner extent is not evidence of a decoded basic block,
compiled code, or runtime reachability. Only counts are printed.
"""
import argparse
from bisect import bisect_right
import csv
from hashlib import sha256
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from resume_switch_v697 import SHA, START, decode


def seeds(path):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError("unsupported executable build")
    off, = unpack_from('<Q', blob, 32)
    n, = unpack_from('<H', blob, 56)
    ph = list(iter_unpack('<II6Q', blob[off:off+56*n]))

    def segment(kind):
        (p,) = (p for p in ph if p[0] == kind)
        return p, memoryview(blob)[p[2]:p[2]+p[5]]

    (rx,) = (p for p in ph if p[0] == 1 and p[1] & 1)
    lo, hi = rx[3], rx[3]+rx[5]
    def read(pc, size):
        start = rx[2]+pc-lo
        return blob[start:start+size]

    cases, default = decode(read(START,35),START,read,lo,hi)
    eh, hdr = segment(0x6474e550)
    version, ptr, count, encoding, _, size = unpack_from('<4BiI', hdr)
    if (version, ptr, count, encoding) != (1, 0x1b, 3, 0x3b) or 12+8*size > len(hdr):
        raise ValueError('unexpected unwind table')
    unwind = {eh[3]+delta for delta, _ in iter_unpack('<ii', hdr[12:12+8*size])}
    _, dyn = segment(2)
    _, link = segment(0x61000000)
    tags = dict(iter_unpack('<QQ', dyn))
    rel = set()
    for at, size in ((0x29,0x2d),(0x2f,0x31)):
        pos, length = tags[0x61000000+at], tags[0x61000000+size]
        if pos+length > len(link):
            raise ValueError('unexpected relocation span')
        rel.update(addend for _, info, addend in iter_unpack('<QQq', link[pos:pos+length])
                   if info == 8 and lo <= addend < hi)
    return (lo,hi), {'unwind': unwind, 'relocation_only_rx': rel-unwind,
                     'switch_without_unwind_or_relocation': set((*cases,default))-unwind-rel}


def scanner(path, rx):
    ends = {}
    with path.open(encoding='utf-8', newline='') as f:
        rows = csv.reader(f, delimiter='\t')
        if next(rows, None) != ['address','size','instructions','undecodable']:
            raise ValueError('unexpected scanner header')
        for address, size, insns, bad in rows:
            p = int(address,16)
            n, i, b = map(int,(size,insns,bad))
            if p in ends or not rx[0] <= p < p+n <= rx[1] or not 0 <= b <= n or i < 0:
                raise ValueError('invalid scanner row')
            ends[p] = p+n
    return ends


def compare(groups, ends):
    starts = sorted(ends)
    furthest = []
    for p in starts:
        furthest.append(max(ends[p],furthest[-1] if furthest else 0))
    result = {}
    for name, group in groups.items():
        exact = interior = 0
        for p in group:
            if p in ends:
                exact += 1
            else:
                i = bisect_right(starts,p)-1
                interior += i >= 0 and p < furthest[i]
        result[name] = dict(exact=exact, inside_extent_only=interior, absent=len(group)-exact-interior)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--functions',type=Path)
    a = p.parse_args()
    rx, groups = seeds(a.eboot)
    print(json.dumps(compare(groups,scanner(a.functions,rx)) if a.functions else
                     {name:len(entries) for name,entries in groups.items()}, sort_keys=True))
