#!/usr/bin/env python3
"""Offline relocation inventory for sectionless PS4 ELF64; emits only counts."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct


def audit(b):
    def read(fmt, off):
        if off < 0 or off + struct.calcsize(fmt) > len(b):
            raise ValueError('truncated ELF field')
        return struct.unpack_from(fmt, b, off)

    if b[:6] != b'\x7fELF\x02\x01' or read('<HH', 16) != (0xfe10, 62):
        raise ValueError('expected little-endian PS4 executable ELF64')
    phoff, = read('<Q', 32)
    entsize, count = read('<HH', 54)
    if entsize != 56 or not count or phoff + count*56 > len(b):
        raise ValueError('bad program header table')
    loads, special = [], {}
    for i in range(count):
        typ, flags, off, va, _, filesz, memsz, _ = read('<II6Q', phoff+i*56)
        if off + filesz > len(b):
            raise ValueError('segment extends past EOF')
        if typ == 1:
            if filesz > memsz or va + memsz > (1 << 64):
                raise ValueError('invalid PT_LOAD extent')
            loads.append((va, va+memsz, flags, off, filesz))
        elif typ in (2, 0x61000000, 0x6474e550):
            if typ in special:
                raise ValueError('duplicate dynamic/unwind segment')
            special[typ] = off, va, filesz
    if not loads or len(special) != 3:
        raise ValueError('missing load, dynamic, dynlibdata or unwind segment')
    loads.sort()
    if any(a[1] > z[0] for a,z in zip(loads, loads[1:])):
        raise ValueError('overlapping loads')
    eh, ev, es = special[0x6474e550]
    if read('<4B', eh) != (1, 0x1b, 3, 0x3b):
        raise ValueError('unsupported unwind index encoding')
    n, = read('<I', eh+8)
    if n*8+12 > es:
        raise ValueError('truncated unwind index')
    starts = set()
    for i in range(n):
        pc, = read('<i', eh+12+8*i)
        starts.add(ev+pc)
    do, _, ds = special[2]
    tags = {}
    for p in range(do, do+ds-15, 16):
        k,v = read('<QQ', p)
        if k == 0:
            break
        tags[k] = v
    else:
        raise ValueError('missing DT_NULL')
    base, _, size = special[0x61000000]
    if tags.get(0x61000033) != 24:
        raise ValueError('unsupported RELA entry size')
    types, relative = Counter(), Counter()
    seen = set()
    for t,s in ((0x6100002f,0x61000031),(0x61000029,0x6100002d)):
        off, length = tags.get(t,-1), tags.get(s,-1)
        if min(off,length) < 0 or length%24 or off+length > size:
            raise ValueError('bad RELA table extent')
        for p in range(base+off, base+off+length, 24):
            slot, info, addend = read('<QQq',p)
            kind = info & 0xffffffff
            if slot in seen:
                raise ValueError('duplicate relocation slot')
            seen.add(slot)
            types[kind] += 1
            if kind != 8:
                continue
            if not any(lo <= slot <= hi-8 for lo,hi,*_ in loads):
                raise ValueError('relative slot outside PT_LOAD')
            target = next((flags for lo,hi,flags,*_ in loads if lo <= addend < hi),0)
            label = ('unwind_start' if addend in starts else 'exec_segment_other') if target & 1 else ('nonexec_load' if target else 'outside_load')
            relative[label] += 1
    return dict(unwind_entries=n, unique_unwind_starts=len(starts), relocation_types=dict(types), relative_targets=dict(relative))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf',type=Path)
    a = p.parse_args()
    try:
        print(json.dumps(audit(a.elf.read_bytes()),sort_keys=True))
    except (OSError,ValueError) as e:
        p.exit(2,f'{e}\n')
