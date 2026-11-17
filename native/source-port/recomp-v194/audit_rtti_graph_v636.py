#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline RTTI graph audit for the pinned 1.09 game, not a runtime binder."""
from collections import Counter
import struct

FORMS = {'pZ9WXcClPO8': 'single', 'byV+FWlAnB4': 'plain', '9ByRMdo7ywg': 'multiple'}


def graph(records, relative, read):
    counts = Counter()
    edges = {}
    names = set()
    intervals = []
    for start, form in sorted(records.items()):
        if start % 8 or form not in FORMS.values():
            raise ValueError('invalid descriptor identity')
        name = relative.get(start + 8)
        if name is None or name in names:
            raise ValueError('missing or reused RTTI name target')
        names.add(name)
        size = 16
        refs = []
        if form == 'single':
            size = 24
            refs.append(start + 16)
        elif form == 'multiple':
            flags, n = struct.unpack('<II', read(start + 16, 8))
            if flags & ~3 or not 0 < n <= 64:
                raise ValueError('invalid multiple-inheritance header')
            size = 24 + 16*n
            for i in range(n):
                field = start + 24 + 16*i
                (offset_flags,) = struct.unpack('<q', read(field + 8, 8))
                if offset_flags & 0xfc:
                    raise ValueError('invalid base flags')
                counts['virtual_edges'] += bool(offset_flags & 1)
                counts['public_edges'] += bool(offset_flags & 2)
                refs.append(field)
        if len(read(start, size)) != size or (intervals and intervals[-1] > start):
            raise ValueError('invalid descriptor extent')
        intervals.append(start + size)
        bases = [relative.get(field) for field in refs]
        if any(base not in records for base in bases):
            raise ValueError('base not in audited descriptor set')
        edges[start] = bases
        counts[form] += 1
        counts['base_edges'] += len(bases)

    pending = {k: len(v) for k, v in edges.items()}
    users = {k: [] for k in edges}
    for child, bases in edges.items():
        for base in bases:
            users[base].append(child)
    ready = [k for k, n in pending.items() if n == 0]
    seen = 0
    while ready:
        base = ready.pop()
        seen += 1
        for child in users[base]:
            pending[child] -= 1
            if pending[child] == 0:
                ready.append(child)
    if seen != len(edges):
        raise ValueError('cycle in RTTI base graph')
    return dict(counts)


def main():
    import argparse
    import hashlib
    import json
    from pathlib import Path
    from audit_modules_v628 import PINS, file_reader, link_tables

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot', type=Path)
    parser.add_argument('libc', type=Path)
    args = parser.parse_args()
    eboot, libc = args.eboot.read_bytes(), args.libc.read_bytes()
    if tuple(hashlib.sha256(b).hexdigest() for b in (eboot, libc)) != PINS[:2]:
        parser.error('unsupported eboot/libc hash or module order')
    game, provider = {}, {}
    link_tables(eboot, details=game)
    link_tables(libc, details=provider)
    loads, read_file = file_reader(eboot)
    def read(va, size):
        (seg,) = (p for p in loads if p[0] == 1 and p[3] <= va <= p[3] + p[5] - size)
        return read_file(seg[2] + va - seg[3], size)

    records = {}
    for key, sites in game['imports'].items():
        nid, module, library = key
        if nid not in FORMS or module != ('libc', 257) or library != ('libc', 1):
            continue
        ((kind, _, size),) = provider['exports'][key]
        if (kind, size) != (1, 48):
            raise ValueError('unexpected RTTI vtable export')
        for slot, reloc, addend in sites:
            if (reloc, addend) != (1, 16) or slot in records:
                raise ValueError('unexpected RTTI address point')
            records[slot] = FORMS[nid]
    if set(records.values()) != set(FORMS.values()):
        raise ValueError('missing RTTI form')
    relative = {slot: addend for slot, info, addend in game['relocations'] if info == 8}
    print(json.dumps(graph(records, relative, read), sort_keys=True))


if __name__ == '__main__':
    main()
