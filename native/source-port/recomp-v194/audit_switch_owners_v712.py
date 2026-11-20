# SPDX-License-Identifier: GPL-2.0-or-later
"""Group V711 switch edges by verified FDE extents, never by nearest start."""
import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from audit_switch_v711 import scan
from resume_switch_v697 import SHA


def extents(code, base, header, length):
    v, ep, ec, et, delta, count = unpack_from('<4BiI', code, header)
    if (v, ep, ec, et) != (1, 0x1b, 3, 0x3b) or 12+8*count > length:
        raise ValueError('unsupported unwind header')
    begin = header+4+delta
    if not 0 <= begin < header <= len(code)-length:
        raise ValueError('invalid frame span')
    result = {}
    for rel, frame in iter_unpack('<ii', memoryview(code)[header+12:header+12+8*count]):
        p = header+frame
        if not begin <= p <= header-16:
            raise ValueError('invalid FDE offset')
        size, cie_delta, start, span = unpack_from('<IIiI', code, p)
        cie = p+4-cie_delta
        if not (12 <= size <= header-p-4 and begin <= cie < p-8):
            raise ValueError('invalid FDE extent')
        cs, tag = unpack_from('<II', code, cie)
        fmt = code[cie+8:cie+4+cs] if 8 <= cs <= p-cie-4 and not tag else b''
        if not fmt.startswith((b'\x01zR\0\x01\x78\x10\x01\x1b',
                               b'\x01zPLR\0\x01\x78\x10\x07\x9b')) or (
                fmt.startswith(b'\x01zPLR') and fmt[15:17] != b'\x1b\x1b'):
            raise ValueError('unsupported CIE encoding')
        at = header+rel
        if at != p+8+start or at in result or not 0 <= at < at+span <= len(code):
            raise ValueError('invalid PC range')
        result[at] = at+span
    return sorted((base+a,base+b) for a,b in result.items()), begin


def classify(rows, ranges):
    starts = [a for a,_ in ranges]
    if any(b > c for (_,b),(c,_) in zip(ranges,ranges[1:])):
        raise ValueError('overlapping FDEs: ownership is ambiguous')
    def owner(pc):
        i = bisect_right(starts,pc)-1
        return i if i >= 0 and pc < ranges[i][1] else None
    totals = Counter(tables=0, dispatcher_in_fde=0, same_fde=0, different_fde=0, no_fde=0,
                     dispatcher_without_fde=0, complete_same_fde=0)
    for pc, _, cases, default in rows:
        totals['tables'] += 1
        source = owner(pc)
        totals['dispatcher_in_fde' if source is not None else 'dispatcher_without_fde'] += 1
        complete = source is not None
        for dst in set((*cases,default)):
            target = owner(dst)
            totals['no_fde' if target is None else 'same_fde' if target == source else 'different_fde'] += 1
            complete &= target is not None and target == source
        totals['complete_same_fde'] += complete
    return totals


def audit(path):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable build')
    off, = unpack_from('<Q',blob,32)
    n, = unpack_from('<H',blob,56)
    ph = list(iter_unpack('<II6Q',blob[off:off+56*n]))
    (rx,) = (p for p in ph if p[0]==1 and p[1]&1)
    (eh,) = (p for p in ph if p[0]==0x6474e550)
    header = eh[3]-rx[3]
    if eh[2] != rx[2]+header:
        raise ValueError('unwind header does not match RX mapping')
    code = blob[rx[2]:rx[2]+rx[5]]
    ranges, _ = extents(code,rx[3],header,eh[5])
    return dict(classify(scan(code,rx[3]),ranges),fde_count=len(ranges))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    print(json.dumps(audit(p.parse_args().eboot),sort_keys=True))
