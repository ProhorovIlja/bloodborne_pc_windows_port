# SPDX-License-Identifier: GPL-2.0-or-later
"""Cross-check bounded switch owners against direct setjmp calls, offline.

FDE ownership is not necessarily the donor's function ownership. Only decoded
E8 calls to the known import stub count. No game addresses are printed.
"""
import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import iter_unpack, unpack_from
import subprocess
from tempfile import TemporaryDirectory

from audit_switch_flow_v714 import decode, extents, scan, walk, SHA


def setjmp_stub(ph, blob, code, base):
    def segment(kind):
        (p,) = (p for p in ph if p[0] == kind)
        return memoryview(blob)[p[2]:p[2]+p[5]]
    tags = dict(iter_unpack('<QQ', segment(2)))
    link = segment(0x61000000)
    def table(a, b):
        pos, size = tags[0x61000000+a], tags[0x61000000+b]
        if pos+size > len(link):
            raise ValueError('dynamic table outside link segment')
        return link[pos:pos+size]
    strings, symbols = bytes(table(0x35, 0x37)), table(0x39, 0x3f)
    slots = set()
    for slot, info, addend in iter_unpack('<QQq', table(0x29, 0x2d)):
        if info & 0xffffffff != 7 or addend:
            continue
        name, _, _, section = unpack_from('<IBBH', symbols, (info >> 32)*24)
        if not section and strings.startswith(b'gNQ1V2vfXDE#', name):
            slots.add(slot)
    (slot,) = slots
    (stub,) = (base+i for m in re.finditer(rb'\xff\x25', code) if
               (i := m.start())+6 <= len(code) and
               base+i+6+unpack_from('<i', code, i+2)[0] == slot)
    return stub


def direct_calls(data, start, insns, target):
    return {pc for pc, (n, op, _) in insns.items()
            if op in ('call', 'callq') and n == 5 and 0 <= pc-start <= len(data)-5
            and data[pc-start] == 0xe8
            and pc+5+unpack_from('<i', data, pc-start+1)[0] == target}


def audit(path, objdump):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable build')
    off, = unpack_from('<Q', blob, 32)
    n, = unpack_from('<H', blob, 56)
    ph = list(iter_unpack('<II6Q', blob[off:off+56*n]))
    (rx,) = (p for p in ph if p[0] == 1 and p[1] & 1)
    (eh,) = (p for p in ph if p[0] == 0x6474e550)
    base = rx[3]
    code = blob[rx[2]:rx[2]+rx[5]]
    stub = setjmp_stub(ph, blob, code, base)
    ranges, _ = extents(code, base, eh[3]-base, eh[5])
    starts = [a for a, _ in ranges]
    if any(b > c for (_, b), (c, _) in zip(ranges, ranges[1:])):
        raise ValueError('overlapping FDEs')
    owners = {}
    for pc, _, cases, default in scan(code, base):
        i = bisect_right(starts, pc)-1
        if i < 0:
            raise ValueError('switch has no owner')
        a, b = ranges[i]
        jump = pc+4+(2 if code[pc-base+4] == 0x77 else 6)+14
        if not a <= pc < jump < b or any(not a <= t < b for t in (*cases, default)):
            raise ValueError('cross-FDE switch')
        group = owners.setdefault((a, b), {})
        if jump in group:
            raise ValueError('duplicate switch jump')
        group[jump] = set(cases)
    out = Counter(owners=len(owners), tables=0, case_edges=0, call_owners=0,
                  call_sites=0, call_tables=0, call_case_edges=0,
                  reachable_call_owners=0, reachable_call_sites=0)
    with TemporaryDirectory(prefix='bb715-') as tmp:
        sample = Path(tmp)/'code.bin'
        for (a, b), switches in sorted(owners.items()):
            data = code[a-base:b-base]
            sample.write_bytes(data)
            listing = subprocess.check_output([objdump, '-D', '-b', 'binary', '-m', 'i386:x86-64',
                                               '--insn-width=16', str(sample)], text=True)
            insns = decode(listing, a)
            if a not in insns or any(j not in insns for j in switches):
                raise ValueError('missing entry or switch boundary')
            calls = direct_calls(data, a, insns, stub)
            reached, _, _ = walk(data, a, insns, switches)
            edges = sum(map(len, switches.values()))
            out.update(tables=len(switches), case_edges=edges, call_owners=bool(calls),
                       call_sites=len(calls), call_tables=len(switches) if calls else 0,
                       call_case_edges=edges if calls else 0,
                       reachable_call_owners=bool(calls & reached),
                       reachable_call_sites=len(calls & reached))
    return dict(out), sorted(a for a, _ in owners)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('--objdump', default='objdump')
    p.add_argument('--private-owner-list', type=Path, help='exclusive local output for donor --file')
    a = p.parse_args()
    counts, owners = audit(a.eboot, a.objdump)
    if a.private_owner_list:
        with a.private_owner_list.open('x') as f:
            f.writelines(f'{addr:#x}\n' for addr in owners)
    print(json.dumps(counts, sort_keys=True))


if __name__ == '__main__':
    main()
