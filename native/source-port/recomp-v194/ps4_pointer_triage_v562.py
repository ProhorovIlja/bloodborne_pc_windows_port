#!/usr/bin/env python3
"""Offline RX pointer triage; emits counts, not a code/data classification."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
from ps4_relocation_audit_v561 import audit


def runs(pairs):
    group = []
    for slot, target in sorted(pairs):
        if group and slot != group[-1][0]+8:
            yield group
            group = []
        group.append((slot, target))
    if group:
        yield group


def thunk_target(buf, va):
    # Strict SysV this-adjustor: add/sub imm8 to RDI; jmp rel32.
    if (len(buf) == 9 and buf[:3] in (b'\x48\x83\xc7', b'\x48\x83\xef')
            and buf[3] and buf[4] == 0xe9):
        return va+9+int.from_bytes(buf[5:], 'little', signed=True)
    return None


def triage(b):
    inventory = audit(b)
    phoff = struct.unpack_from('<Q', b, 32)[0]
    count = struct.unpack_from('<H', b, 56)[0]
    loads, segments = [], {}
    for i in range(count):
        t, f, o, v, _, n, _, _ = struct.unpack_from('<II6Q', b, phoff+56*i)
        segments[t] = o, v, n
        if t == 1:
            loads.append((v, v+n, o, f))

    def offset(va, size, flags=0):
        return next((o+va-lo for lo,hi,o,f in loads if lo<=va<=hi-size and f&flags==flags), None)

    do, _, ds = segments[2]
    tags = {}
    for i in range(do, do+ds-15, 16):
        k,v = struct.unpack_from('<QQ', b, i)
        if not k:
            break
        tags[k] = v
    base = segments[0x61000000][0]
    rel = {}
    occupied = set()
    for t,s in ((0x6100002f,0x61000031),(0x61000029,0x6100002d)):
        o,n = tags[t], tags[s]
        for slot,k,a in struct.iter_unpack('<QQq',b[base+o:base+o+n]):
            occupied.add(slot)
            if k==8:
                rel[slot] = a
    if len(rel) != inventory['relocation_types'].get(8,0):
        raise ValueError('inconsistent relative relocation inventory')
    eh, ev, _ = segments[0x6474e550]
    anchors = {ev+struct.unpack_from('<i',b,eh+12+8*i)[0]
               for i in range(inventory['unwind_entries'])}
    rx = {s:a for s,a in rel.items() if offset(a,1,1) is not None}
    unknown = Counter(a for a in rx.values() if a not in anchors)
    mixed, strong = Counter(), Counter()
    mixed_runs = null_header_runs = 0
    for run in runs(rx.items()):
        if len(run)<3 or not any(a in anchors for _,a in run):
            continue
        nonanchors = [a for _,a in run if a not in anchors]
        if not nonanchors:
            continue
        mixed_runs += 1
        mixed.update(nonanchors)
        s = run[0][0]
        p = offset(s-16,16)
        if p is not None and s-16 not in occupied and s-8 not in occupied:
            top, rtti = struct.unpack_from('<qQ',b,p)
            if -0x100000 <= top <= 0 and top%8==0 and rtti==0:
                null_header_runs += 1
                strong.update(nonanchors)
    thunks = set()
    for a in unknown:
        p = offset(a,9,1)
        if p is not None and thunk_target(b[p:p+9],a) in anchors:
            thunks.add(a)
    return dict(rx_nonanchor_slots=sum(unknown.values()), rx_nonanchor_targets=len(unknown),
                mixed_runs=mixed_runs, mixed_slots=sum(mixed.values()), mixed_targets=len(mixed),
                null_header_runs=null_header_runs, null_header_slots=sum(strong.values()),
                null_header_targets=len(strong), strict_adjustor_targets=len(thunks),
                strict_adjustor_slots=sum(unknown[a] for a in thunks))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf', type=Path)
    try:
        print(json.dumps(triage(p.parse_args().elf.read_bytes()),sort_keys=True))
    except (OSError, ValueError, struct.error) as e:
        p.exit(2,f'{e}\n')
