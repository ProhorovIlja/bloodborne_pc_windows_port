# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline Bloodborne EMEVD structural audit; no event opcode execution.

Layout reference: JKAnderson/SoulsFormats, Formats/EMEVD.
Only totals are emitted. Inputs must be explicitly selected local DCX files.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from struct import Struct

from dcx_dflt_v708 import unpack

HEAD = Struct('<8sII16q')
EVENT = Struct('<5q2I')
INSN = Struct('<2i3q')
MAX = 32 << 20


def span(offset, count, unit, limit):
    if offset < 0 or offset > limit or count < 0 or count > (limit-offset)//unit:
        raise ValueError('span outside parent section')
    return offset + count*unit


def audit(raw):
    if len(raw) < HEAD.size:
        raise ValueError('short EMEVD header')
    tag, version, size, *fields = HEAD.unpack_from(raw)
    if (tag, version, size) != (b'EVD\0\0\xff\0\0', 0xcc, len(raw)):
        raise ValueError('not a Bloodborne-format EMEVD payload')
    sections = list(zip(fields[::2], fields[1::2]))
    if sections[2][0]:
        raise ValueError('unsupported unknown section')
    spans = []
    for (count, offset), unit in zip(sections, (48, 32, 1, 32, 32, 8, 1, 1)):
        if offset < HEAD.size:
            raise ValueError('section overlaps header')
        end = span(offset, count, unit, size)
        if count:
            spans.append((offset,end))
    spans.sort()
    if any(a[1] > b[0] for a,b in zip(spans,spans[1:])):
        raise ValueError('overlapping sections')
    (ne, eo), (ni, io), _, _, (np, _), _, (na, _) = sections[:7]
    refs = []
    for idx in range(ne):
        _, n, off, pn, poff, rest, pad = EVENT.unpack_from(raw, eo+idx*EVENT.size)
        if rest > 2 or pad:
            raise ValueError('invalid event metadata')
        for count, start, unit, limit in ((n,off,INSN.size,ni), (pn,poff,32,np)):
            if count < 0 or (not count and start not in (0,-1,0xffffffff)):
                raise ValueError('invalid event slice')
            if count and start % unit:
                raise ValueError('invalid event slice')
            if count:
                span(start,count,unit,limit*unit)
        if n:
            refs.append((off//INSN.size, off//INSN.size+n))
    cursor = 0
    for start,end in sorted(refs):
        if start != cursor:
            raise ValueError('instruction ownership overlap or gap')
        cursor = end
    if cursor != ni:
        raise ValueError('unowned instructions')
    for idx in range(ni):
        _, _, n, off, _ = INSN.unpack_from(raw, io+idx*INSN.size)
        if n or off not in (-1,0xffffffff):
            span(off,n,1,na)
    return Counter(files=1, events=ne, instructions=ni, parameters=np, argument_bytes=na)


def read_dcx(path):
    with path.open('rb') as handle:
        data = handle.read(MAX+1)
    if len(data) > MAX:
        raise ValueError('compressed input exceeds limit')
    return unpack(data,max_output=MAX)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('assets',nargs='+',type=Path)
    total = Counter()
    for path in p.parse_args().assets:
        total.update(audit(read_dcx(path)))
    print(json.dumps(total,sort_keys=True))
